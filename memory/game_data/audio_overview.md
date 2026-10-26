# Audio: what the evidence is, and where it stops

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** Start here for audio. It states the scope of the Wwise
evidence and the boundary between an authored link and an observed one, which the
rest of the lane depends on.

## The six layers of audio evidence

1. physical package/media identity;
2. decoded playable media;
3. Wwise Event/action/media graph;
4. authored game consumer and control parameters;
5. validated runtime request;
6. selected branch, audibility, and final DSP behavior.

Evidence may advance only one layer at a time. A stronger downstream fact does
not retroactively make every upstream candidate unique. Layers 5-6 need a host
process or a bounded capture ([`audio_native_hooks.md`](audio_native_hooks.md)).

Audio's runtime model reads stored enum constants with the shared IL2CPP
metadata-default reader. Its F0 payload is a raw little-endian DWORD before
the existing signed transform; the cache schema excludes older numeric
projections. Music-state IDs and callback flags do not prove setter execution,
active state or playback.

Prioritize shared package, codec, HIRC and consumer rules by the current files
or graph cohorts they can advance. A named voice is a possible representative,
not the recovery unit. Reuse recorded observations and offline byte comparisons
before requesting new runtime evidence. A receiver-ownership capture must state
its runtime question separately from any verified file-coverage gain; observing
more entries does not itself decode more files. The common admission and stop
criteria live in the game-data entry point's recovery queue.

The reusable [`package corpus gate`](../../scripts/game_data/wwise_package_corpus.py)
now inventories every available AKPK package under the current authenticated VFS
roster, including hotfix packages. It checks each complete logical payload
against its recorded digest and preserves sector, full-width key, language,
package and row ordinal. The available corpus contains repeated bank identities
across base/hotfix packages and distinct external keys with the same low word.
Therefore neither a bank ID nor a truncated external key is a globally unique
media identity. Keep all candidates until an independent precedence or full-key
join decides them. Header geometry and whole-package bytes do not bind an
existing decoded output or establish the package used by a live handle.

The Windows AKPK language sector is a bounded ID/offset table followed by
NUL-terminated UTF-16LE labels. The reader uses that explicit profile, checks
offsets and unique IDs, and preserves unclaimed bytes; it does not guess a
different encoding. An entry's language ID joins only its own package's table.
An absent ID stays unresolved. Stored labels describe package metadata, not
the spoken language of a decoded clip or the language selected at runtime;
package path names do not replace this join.

The shared AKPK reader also checks each bank entry's transformed BKHD prefix:
the stored bank ID must equal its full bank-sector key, and the declared header
must fit the entry. This establishes a cross-format stored identity, not package
uniqueness. Base/hotfix variants can have different HIRC bodies, including a
different ordering of the same Event action IDs. Preserve package-qualified
bank and object identities and the authored array order; an unordered action
set cannot substitute for the bank's stored data. The typed bank reader
[`hirc_v150.py`](../../scripts/webui/audio/semantics/hirc_v150.py) owns the
body interpretation, while the package corpus gate owns complete-roster and
bank-prefix checks.

The CLI's direct-media filename uses the full `UInt64` entry key; the low word
is a crypto seed, not its filename identity. Its package parser knows the
sector, row ordinal and numeric language, but the WEM entry passed to conversion
drops those fields. Embedded bank media also needs its parent bank entry and
DIDX position: a repeated bank key alone is not a decoded-media collision.
Embedded and direct entries can share a media key while both contain `PLUG`
data, which the CLI skips before naming an output. Count actual write candidates
after that distinction instead of treating every catalog row as playable media.
The current source manifest retains only output path, coarse source-bank folder
and block, with one record per output path. The Python builder consumes that
manifest in a temporary directory and retains only those coarse tags. Existing
`contentSha256` values hash decoded file bytes, not stored package-entry bytes.

The maintained decode producer should persist a versioned receipt per source
occurrence: complete VFS package identity and digest; sector, full-width key,
numeric language, explicitly defined ordinal and extent; embedded bank/DIDX
ancestry when present; stored encoded bytes, clear WEM and decoded output hashes
as distinct stages; decoder identity/configuration and actual output path.
Retain every source occurrence when output names coincide and state which bytes
were written instead of silently replacing a path-keyed receipt. Pass this
structured provenance through the Python metadata/index projection, keeping
full-width keys as strings. This offline pipeline join applies across packages;
repeated single-sound captures cannot replace it. The producer owners are
`EndfieldAkpkPackage`, `EndfieldAudioCli` and the decode/source-metadata path in
[`build_audio.py`](../../scripts/webui/audio/build_audio.py).

Counts change per input set (current `reports/animestudio/hirc_*_current_latest.*`);
this file keeps boundaries, witnessed joins, gaps and corrections. Code owners
under `scripts/webui/audio/`: `build_audio.py`, `semantics/hirc_action_corpus.py`
(lanes, graph), `hirc_named_reach.py` (naming, reach), `hirc_v150.py` (typed
parse), `wwise_enums.py` (SDK enum contract). Layouts: [`audio_hirc_parser.md`](audio_hirc_parser.md);
graph and typed parse: [`audio_hirc_graph.md`](audio_hirc_graph.md); non-HIRC
sections: [`audio_bank_format.md`](audio_bank_format.md).

AudioDialog path hashing and flattened output names are naming rules; neither
a unique current full-key candidate nor a current package digest establishes
the provenance of an existing decoded file. Stored-entry hashes and existing
FLAC hashes can be added independently offline, but proving the historical
conversion edge requires its retained receipt, exact surviving WEM bytes, or an
explicit offline decode/PCM comparison. The full managed
`Voice/<language>/<path>` argument is also distinct
from the physical AKPK catalog identity. Closing this join requires a proved
path-to-entry relation plus a selected-input receipt carrying both encoded
entry and decoded-file hashes. Package/VFS freshness alone does not supply
that missing decode receipt. A selected external-row probe now records both
encoded-entry and decoded-file hashes and compares their decoded PCM exactly.
The row matches a captured voice completion descriptor and its calculated full
path key, closing this bounded offline comparison. The live package backing
pointer still has no recorded file identity, so this does not extend to every
decoded voice or establish game-side decoded output. A combined read recording
now supplies platform completion status/byte counts and local pre-transform
snapshots. The selected voice's transform metadata spans its encoded length,
and its sparse buffer DWORDs match the same installed entry. Numeric and
background cohorts also match sampled encoded bytes in the bounded index.
The reviewed aligned native XOR path agrees with the offline reader; predicted
clear words remain calculations. Full live buffer contents, file-handle
lifetime, game codec identity and final output are separate gaps. Header-only AKPK framing
and shared crypto live in `scripts/game_data/wwise_package.py`; generated
selected-entry inventories and decode receipts stay under `reports/audio/`.
Selected numeric candidates from the same sparse read witness now also have
bounded offline encoded-entry/WEM/FLAC receipts with equal decoded PCM.
They include mono, stereo and four-channel streams, so numeric descriptors
must not all be labelled UI sounds. The reusable
[`selected-entry comparison`](../../scripts/webui/audio/semantics/package_decode_witness.py)
checks exact header/row/sample identity before extraction. Its receipt
projector checks retained selected bytes and current FLAC identity without
repeating decoding; historical decoder results remain explicitly offline.
Static possible Event reaches do not become the Event selected in the capture.
The current projection preserves the broader boundary
in `scripts/webui/audio/semantics/runtime_observations.py`; the request and
native source evidence is documented in [`audio_native_hooks.md`](audio_native_hooks.md).

Audio expression enum labels and selected game-side RTPC names have an independent
current static-name contract. It authenticates the explicitly selected metadata
and native type table, complete named enum declarations, typed literal fields,
and the original selected default-value conversion. The full-width unsigned
literal form reads its payload as little-endian bytes; the current source proof
keeps other encodings and native dispatcher cases outside that admission. These
static names do not validate old Audio callsite arrays, observe setters, choose
live values, or establish DSP behavior. Serialized RTPC alignment also requires
matching current source metadata and exact HIRC IDs; a native gate alone cannot
refresh a stale generated Audio index.

The native queue companion now authenticates the posted Event's exact registry
lookup and the retained Event node/descriptor pair in one queue record. Its
drain forwards the same descriptor allocation and playback serial through that
node's eligible registered Actions. The checked Play Action bank reader and
target setter supply the complete target ID to the execution-time registry
lookup, which returns the retained target primary object. The bank registration
loaders now close authored Action construction and new Event list creation:
resolved distinct Actions retain authored order through intrusive links.
Existing Event IDs skip rereading, missing Actions fail on a partial prefix,
and duplicate/shared Actions can mutate links. Selected node subtype, actual
bank loading and live registry generations remain separate.

The companion also closes the bank source-record to descriptor
match-word join: the node loader installs the stored source ID in the same
source the playback wrapper supplies to the selector. External Source Events
therefore reach an authored slot whose cookie chooses a usable descriptor from
the posted allocation. The supplied descriptor chooses the path or memory;
an Event ID alone does not choose a unique voice file. Stored descriptor order,
skipped incomplete matches, raw codec-argument conversion and provisional
success after failed path allocation are covered by the reviewed
[`queue contract`](../../scripts/game_data/contracts/wwise_source_queue_native.json)
and its [`validator`](../../scripts/game_data/wwise_source_queue_native.py).
They establish a conditional native route, with live queue ownership and
Event selection still open.

The separate
[`codec factory contract`](../../scripts/game_data/contracts/wwise_codec_factory_native.json)
authenticates selected source-kind/full-plugin dispatch and codec registration,
shared media-source construction, native RIFF-prefix parsing and distinct codec
initialization/sample-processing targets.
Original codec initialization reads the selected WEM format prefixes and
produces metadata agreeing with offline PCM rate, channels and sample count.
Selected original Opus code now computes samples from a physical WEM and the
whole media wrapper returns them with correct pre-skip, trim and playback
geometry; the external reference differs by at most one signed-16-bit
quantization step. This is conditional offline PCM evidence with explicit
platform models that compute no samples. Independent isolated host execution
returns exactly the same Opus floats. Selected numeric Event sources now also
execute original resident-row admission, exact-key lookup, whole preparation
and sample publication on the host CPU. The resident fields join the existing
checked LockDataPtr output layout; available table capacity, input lifetime and
provider interfaces remain conditions. Eligible duplicate buffers select the
greatest positive byte count, with latest admitted rows winning equal-size ties
in the checked cohort. Original host Vorbis produces complete playable outputs, with
reference differences reported separately from the larger emulator/host gap.
Original node/source preparation now requests numeric file bytes and executes
allocation/read/publication before the same resident lookup and context PCM.
Immediate and deferred preparation preserve the checked output; open/read/EOF
failures publish no resident bytes. The supplied stream interface selects the
authenticated physical package occurrence. A stronger cohort now executes
original encrypted-header loading, table assignment and list admission before
native numeric row selection and original media XOR; its complete context PCM
is identical. Successful package load prepends, explicit package reprioritization
moves an ID to the head, and lookup selects the first matching key/language row.
The game's load/reorder call sequence and standard-stream/device scheduling
remain conditional. Original synchronous standard-stream reads, Windows
completion/decryption and resident publication now also feed original
memory-provider methods before identical context PCM. Worker dispatch,
read-only handle/metadata association and device/pool state remain supplied.
A successful short OS read is distinct from EOF/error:
native completion can account for requested bytes despite fewer delivered
bytes, so output admission retains actual counts and full-byte hashes.
Original parameter refresh and policy/frame admission now execute with authored
parameter collection excluded. Success can attach an unprepared suppressed
source, so it is not PCM readiness. Original primary/embedded owner construction
also retains the source/node, initializes defaults and acquires references under
supplied object/parameter storage and exclusion input. Original context construction, unity-rate
frame assembly/release, frame preparation and filter bypass reach master-bus
output and sink submission through supplied scheduling and render-client interfaces.
Native frame preparation supplies descriptor fields and corrects the initial
counter; the emitted PCM is exactly the prior complete decoded PCM. Omitting
that step in a separate cohort adds initial silence. A native bus sum checks two
decoded inputs and their gains.
The stronger route cohort executes original attachment into source and bus
lists, nonempty preparation, context gain refresh, bus row admission and matrix
mixing into a separate native PCM allocation, then original bus frame reset.
No helper copies the source descriptor into a bus row. All logical sample
values agree; native accumulation can normalize signed-zero bits. Missing
channel-cache state rolls attachment back, excluded routes/rows produce no bus
input, omitted gain refresh leaves bus PCM silent, and omitted bus reset retains
the previous accumulation. Authored bus/output selection and available arena
state remain supplied conditions.
Original sink service negotiation also executes with finite endpoint interfaces:
requested channels can fall back to mix/closest channels, rate mismatch first
tries Windows conversion and then native resampler setup, and failed event,
buffer or initial silence release prevents successful setup. The complete
matched-format route cohort uses that native sink allocation and per-frame
capacity query, with no helper capacity/valid-count assignment. A full endpoint
can return query success with zero available quanta. Real endpoint selection,
COM/device execution and continuous resampled sink PCM remain open.
Original whole Sound loading and own-property collection now compose with
that negotiated output path. The native property-slot map joins volume and
makeup gain to their distinct owner/context/source gain paths, while authored
low-pass controls activate original source filters. Complete submitted sample
values match independent selected AVX/FMA gain arithmetic from the captured
native filtered PCM, including terminal fades and padded filter history.
Preserve constructor filter flags; forced bypass flags invalidate this cohort.
Empty parent/bus/controller state remains an explicit condition. Stored
ActorMixer ancestry and its output-bus override identify the next native
registry/recursive-collection join; Sound own properties do not establish
effective game loudness.
The separate inherited cohort now authenticates whole parent/bus loaders,
registry/link fixups and settings/default consumers, with a reusable STMG reader
and authenticated available-bank census. An initialized empty parameter manager
differs from physical bank defaults. Original default/transition setters and
recursive collection now compose through source filters, native mixing and
finite render buffers; every submitted sample value passes the independent
gain check. The original null-component fallback constructs default listener
state, whose empty vectors remain unchanged. A supplied single mixer bus still
differs from the loaded authored bus ancestry. A corrected phase capture now
observes component/listener returns, completed Action-to-selector transport,
constructed-owner continuity into nonzero PCM and sampled context/bus routes.
Complete native voice paths match external package entries, and a finite
nonzero live prefix exactly matches original native decoding of one matching
physical WEM. These sparse joins retain explicit allocation/lifetime and
package-selection conditions. The device phase capture now observes successful
same-invocation buffer requests, byte-exact sink/render prefix copies and
successful Windows release results. This closes sampled API submission, while
complete source-to-mixed-frame attribution and allocation generations still need
the targeted evidence described in
[`runtime_capture_requirements.md`](../runtime_capture_requirements.md#audio-event-owner-listener-and-output-selection).
Caller review now excludes an incorrectly declared historical mixer-row array:
those recipes read result-storage bytes, while independent route source/bus fields
remain valid. Mixer capture now supplies the actual row array and completed
output conversion; recorded constant gain reproduces the saved first-channel
output prefix. The initial current-serial read used a neighboring word and is
excluded. The corrected repeat now observes nonzero stored serials beside PCM,
with unique managed Event candidates and complete local source/owner transport
tuples for a subset. Another voice prefix independently matches original native
decoding from its matching physical WEM. Observed source-buffer reuse leaves
multiple Event candidates for some mixer storage. Frame capture now retains
paired bus input/output, descriptor publication and unsampled source/reset
endpoints. A subset connects current source identity to native published mixer
inputs within observed intervals. Actual gain/matrix/filter processing and
device-frame identity remain open. Numeric reads are captured, but queue loss
withholds that session's source/write/reset joins. Completed numeric pairs remain
local observations. Attribution/address bugs are patched and both saved sessions
replayed; numerical operands, frame handoff and bounded recording scope still
block further capture requests. No global frame
or whole Event contribution is inferred from storage.
Live package/provider choice, pointer generations, inherited owner/route/effect
state, varying pitch/rate, complete device negotiation/processing history and
audibility remain open. Details stay in
[`audio_native_hooks.md`](audio_native_hooks.md).

Representative complete external rows now have fresh physical-package,
encoded-entry, clear-WEM, decoded-FLAC and exact PCM comparisons across Vorbis
and Opus. These extend playable-file provenance for the selected rows. Saved
source-bridge text is an input to the conditional full-path key calculation;
string equality does not join its source lifetime to a different recording's
file handle or establish which eligible Event was posted. Retain the full
package-qualified receipt and that distinction when composing the layers.
[`audio_native_hooks.md`](audio_native_hooks.md) owns the selection and
current offline comparison boundary; changing receipts remain in
`reports/audio/`.

Direct authored UI Event routes now also have physical-bank Event/Play/Sound
and numeric sound-package row witnesses with exact offline WEM/FLAC PCM
agreement. Their memory-labelled sources occur in banks without embedded
media sections; the sound bytes live in a separate package. Buffering policy
therefore cannot choose physical storage. These are selected bank/package
occurrences and playable source content. Conditional native resident-pointer
acquisition and whole media preparation are now checked offline; live
bank/media selection, actual game package/provider choice, effects and device output remain
outside the proof.

## The structural lanes

**One proof pattern.** Each numeric HIRC type has a current-corpus lane bound to
the authenticated VFS input set (verified package hashes, chunks and physical
sources joined to the outer ledger, reconciled per bank and per package). Its
grammar is the SDK deserializer's, not a fit. The constraining checks are that
framed body bytes equal declared object bytes minus object ids and that every
exact body ends at its declared end; `exactCursorBytes + nonExactBodyBytes =
bodyBytes` is an internal assert that cannot fail. A failed, unsupported or
ambiguous body publishes `incomplete` and exits nonzero. `failed = 0` is partly
upstream: a malformed `0x02` source prefix aborts its package in the prefix
census before reaching a body lane. **Exact framing never establishes** operation
names, field ownership, targets, execution, selection or audibility unless a
separate gate says so.

| type | what the lane frames | what it does not claim |
| --- | --- | --- |
| `0x03` Action | whole cursor; serialized action type is a 16-bit word | execution; see target-word notes below |
| `0x02` Sound | 14-byte source prefix (plug-in id, source id at `+5`) plus the nine shared node groups to the declared end | source identity beyond the media join, cross-bank relations |
| `0x04` Event | one-byte count plus 32-bit entries | the entries' targets' names |
| `0x07`, `0x05`, `0x06`, `0x09` | shared node frame plus each container tail (child vectors; `0x05` adds an opaque block and an 8-byte record vector with an independent count, `referenceRecordCountMismatch`; `0x06` adds group lists and 14-byte records; `0x09` layers with their own RTPC curves) | ordering, selection, membership semantics |
| every other shipped type | byte-exact from the SDK: `0x08`/`0x12` bus, `0x0A`-`0x0E` (`0x0C` trees walked against `AkDecisionTree::ResolvePath`), `0x10`, `0x11`, `0x13`-`0x16`; `0x0F` unshipped, fixture only | see [`audio_hirc_parser.md`](audio_hirc_parser.md) |

- **The structural lane is closed**; what remains is inside plug-in parameter
  blocks. A refreshed client (the `HotfixAudio` cohort) added objects and closed
  every type and graph reference without a grammar change; the named gate covers
  only its managed-literal identities, so new names from other sources are open.
- When lanes share code, **keep each lane's own layout sentence and non-claims**:
  unifying them once silently dropped `0x02`'s source-identity and cross-bank
  disclaimers, which counts alone could not reveal.

## Corrections the corpus could not force by itself

Durable lessons; each has a published histogram or counter.

- **Group I key is variable-size.** `0x02` spends one byte on every key, so a
  fixed width survived that corpus and would have mis-framed the `0x07` objects
  with wider keys (`groupIKeyWidth_*`). Its five-byte cap and 32-bit range are
  inherited from the `0x03` reader, not proven here.
- **Group H state is variable-length** (`u32 id`, `u16` count, then `count` x
  `u16 AkPropID` and `count` x `u32` value, from
  `CAkStateAware::ReadStateChunk`). A fixed twelve bytes survived three whole
  corpora because every state had one element; `0x09` carries two
  (`groupHStateWidth_*`). **A width a one-dimension sweep calls uniquely
  determined is unique only over the shapes the corpus contains.**
- Group E selector `0x01` appears without the extension, disproving a bit-0
  predicate (thin: very few objects); selector `0x02` is unobserved and the
  reader follows the engine. Group B is empty in every shipped body; its
  six-byte element comes from the SDK reader and a fixture.
- **The action type is the whole 16-bit word.** Framing keys on the high byte,
  but that mask had become the published identity (four Stop words all shown as
  `stop`). The contract names all but `0x1B02`/`0x1B03`, which stay unnamed: the
  stock enum stops at `0x1B01` and a low-byte-pattern name would be fitted.
  **A mask chosen because it decides a layout quietly becomes identity.**
- **The RTPC type is `AkGameSyncType`**, not `AkRtpcCurve::OwnerType`
  (`AkRtpcCurveParams.rtpcType` in the PDB; `ReadRtpcCurves` reads the byte into
  it; 5/8 are markers). The corpus exercises `GameParameter` and `Modulator`.
  Naming the field proves no live value or curve activation.

## The reference graph (layer 3 closes, layer 4 opens)

- **The terminal vectors of `0x04`/`0x05`/`0x06`/`0x07`/`0x09` are object
  identities**: every counted reference resolves to exactly one object declared
  in the same bank, with no self reference, no target with two referrers, no
  cycle, and a longest chain of 8 references. Every such number is computed by
  the reader. A few object ids repeat inside a bank; no reference targets one.
- **`0x06` is where the join said no.** Only its child vector resolves
  completely; unmatched group-item and record words are published as
  `candidateWords` and not joined (the first attempt claimed all three vectors
  and the gate failed it). **Believe the counter and narrow the claim.**
- **Correction: action targets cross banks and packages.** The same-bank result
  is a fact about those counted vectors, not the corpus. The `0x03` target word
  names an object in another bank of the same package, or in another package,
  far above the ~1.5 hits chance predicts (~1,460x). Targets outside the reader's
  package are counted as outside, not unresolved, and the gate asserts that the
  crossing is observed so a future zero cannot restore the old claim. The first
  body byte clearly matters (`action_03` carries nearly every in-bank
  resolution, `action_04` resolves for under 1% of its targets) but is
  **reported, not claimed as a decider**: no class is clean the way the plug-in
  partition below is, so a rule would be fitted.
- **Two corpora, one object apart**: the structural gate audits every AKPK
  package, the WebUI bank reader only bank/hotfix packages (missing
  `audit_stream.pck`). Quote which corpus a count came from; see the comment on
  `build_audio.EVENT_BANK_FILE_REGEX`.

## Naming: what the shipped literals reach

- **The test is a computed coincidence rate, not a vocabulary.** A folded
  `AudioHashGenerator` hash of a structural-shape literal hits a type by chance
  with probability `population / 2**32`. `0x04`, `0x08` (bus-shaped names) and
  `0x15` (device-shaped names, 4 of its 5 objects) clear it by three to five
  orders of magnitude -- the shapes describe the strings, not what the types
  do; `0x02` matches at its own coincidence rate, so its
  name-like matches are reported and **not** claimed. The gate applies the bar
  to every type and refuses a pass where nothing clears it. The narrow
  `au_`/`bark_`/`radio_` prefix claim is gated separately.
- **Sixteen types match no literal** (`0x03`, `0x05`-`0x07`, `0x09`, `0x0A`-`0x0E`,
  `0x10`-`0x14`, `0x16`): their anonymity is a property of the data.
- **Bank ids are named; media ids are not** (zero, against an expectation
  under one): the identifier chain ends at an opaque media id, so do not look
  for a filename. No named bank id is also a HIRC object id.
- **The chain is closed: shipped identifier -> media file.** The named walk runs
  package-wide (`walkEdgesLeavingThePackage`; a per-bank walk abandoned
  sibling-bank edges) and includes `0x09` child vectors (layer containers sit
  between many named Events and their sounds). It publishes the reached ids
  with the counts and refuses a count without its list. Matched objects exceed
  identifiers because a few named objects are declared in two packages, which is
  expected. Music containers are not in this walk.
- **The plug-in id decides whether a source names shipped media.** Joining the
  `0x02` source id to AKPK media ids, `0x00040001` and `0x00140001` always name
  shipped media; `0x00080001`, `0x00640002`, `0x00650002`, `0x00940002` and
  `0x01990002` never do; no plug-in id is split and the gate enforces that. The
  low nibble does not explain it (`0x00080001` is type 1 and never resolves).
  **Compute this across the whole corpus, never per package** (the
  cross-package trap in [`audio_naming_coverage.md`](audio_naming_coverage.md)).
  `hirc_v150.HIRC_SOURCE_PLUGIN_LABELS` names them (Vorbis, Opus; External
  Source, Sine, Silence, Motion Source, Synth One): class identity, not proof
  that a generator or external source runs. Every reached source id with no
  shipped media comes from a never-media plug-in id.

## Non-claims go stale, and nothing makes them fail

Four report non-claims ("media placement unidentified", "target resolution not
established", "entry values unnamed", ...) were right when written and later
falsified by a sibling lane; each report is gated only on what it claims. Treat
"this does not establish X" as dated, and when a conclusion is corrected, grep
every report and docstring that repeated it. Tests pin the scoping.

## The SDK witness

- **The shipped `AkSoundEngine.dll` is Wwise 2023.1.17** with in-house changes:
  its only version string is `wwise_v2023.1.17`, and its assert paths name a
  stock build root and a vendored `RM42.Beyond` tree, so every stock-SDK layout
  must meet the bank bytes (the corpus gates check that; every layout has
  passed). Its hash is pinned in `contracts/wwise_effect_parameters_native.json`.
- The DLL is unpacked (no `.tvm0`), RTTI-stripped and names only the chunk
  tags: **do not string-mine it** for layouts.
- **The witness is the SDK's Profile static libraries and PDBs** (exact version
  2023.1.17.8841): named v150 deserializers that disassemble with `dumpbin`,
  vtable slots resolving from relocation tables, PDB type records for the enum
  contract; `scripts/game_data/wwise_sdk_symbols.py` matches shipped functions
  to them. They are Audiokinetic's under EULA: record derived facts, never
  vendor them, and gate the SDK inputs afresh on each machine.
- **The shipped DLL cannot be profiled** (no communication layer).
- `INIT` names `0x01990002` (source 409) and `0x01FB0007` (sink 507)
  **AkMotion** ([`audio_bank_format.md`](audio_bank_format.md)): authored class
  identity, not registration, instantiation or output.

## Recovery queue

Closed and not to reopen: shared SDK enum naming (unsupported values stay
numeric), bus vocabulary in the typed v150 projection, and the structural
`0x0C` decision-tree walk (child ranges, strict sibling-key order, reachable
nodes, same-bank leaf joins; `+8` is a relative weight and `+10` a
selected-leaf probability gate, so siblings need not sum to 100). Open inside
them: plug-in-specific value tables, leaves with no same-bank declaration,
runtime bus and leaf selection.

1. **Plug-in meanings and processing.** Anonymous bulk-read partitions and
   numeric update transformations are authenticated for Convolution Reverb and
   Mastering Suite. Convolution also has parameter-copy/media-consumer joins,
   a partial IR header/pointer layout, a conditional upper-half-float32 kernel,
   and partial named `powf` correspondence
   ([`audio_hirc_graph.md`](audio_hirc_graph.md)). Mastering's complete serialized
   source joins, parameter retention and section callback bindings are proved;
   the first bank bytes conditionally suppress anonymous sections in its local
   engine. The current-revision section-two consumer is a mapped channel gain,
   with conversion clamps, bounded mask-derived control indices and the native
   sample multiplication proved. Rounded channel width fits the checked stride;
   frame padding and caller allocation remain conditional. Section zero's
   series of second-order IIR kernels, persistent channel histories and identity
   skip are also proved. Its bounded trailing-frame fill is joined to the shared
   byte-fill primitive, and histories advance through those zero frames;
   caller allocation remains open. Section one's
   parallel filtered bands, squared power and smoothed gain histories, periodic
   nonlinear target calculation and band summation are authenticated. All
   section-three kernels are also closed under admitted state: threshold clip,
   asymmetric peak smoothing with unit clip, and delayed window-peak processing
   with gain smoothing and final clip. SIMD constants have proved initializer
   writes into mutable storage. The PE process-attach route and initializer
   pointer table are joined to every needed initializer; successful prerequisites,
   unchanged loader dispatch and later constant lifetime remain conditional.
   An earlier error-returning initializer table also joins the power/time CPU
   selector's writer and its CPUID/XGETBV predicate; modeled hardware responses
   verify the original route while actual selection remains unobserved.
   These are static native facts; the page retains structural read evidence.
   Current section-one and section-three conversion and application also join
   serialized controls to state reads and helper arguments, preserving numerical
   helper boundaries. Crossover coefficient arithmetic, normalization and filter
   history retention are proved; active band histories persist across updates,
   while inactive histories reset. Complete numeric coefficient dispatch now has
   a scalar instruction/expression proof, including both quality-threshold paths
   and the root-zero/unordered skip-division branches;
   helper returns and names remain separate boundaries. The time helper's finite
   scalar and FMA expressions, range predicates and special-value candidates are
   now proved independently, with partial named CRT exponential correspondence.
   Its table and selector join the power helper's authenticated data. NaNs bypass
   the external error routine, while finite overflow/underflow call it. Original
   scalar checks and an explicit AVX floating model preserve those evidence tiers;
   sampled exponential agreement does not establish arbitrary-input equivalence.
   Stored default selection and forwarding are now joined: the band initializer
   passes its legacy payload directly, and the peak initializer compares a fixed
   key against one stored entry using an exact named CRT comparison body before
   forwarding its selector/payload. Application failure and no-match exits are
   distinct. Legacy application has its own arithmetic/routing proof lane;
   mutable pointer lifetime remains a separate gap.
   Converter revision routing is now proved separately: recognized destination
   headers retain an unchecked length word, unknown destinations copy the source
   header, and current-to-old conversion rejects. Legacy control guards expose
   an old-to-current band special/link exception. The old/current peak loops
   correspond after their explicit mode/link and amplitude steps: old application
   retains the extra amplitude array, which delayed mode consumes. The stored
   old default uses mode zero and the normal control pipeline supplies current
   records. Synthetic execution demonstrates that state dependency without
   establishing legacy delayed-mode reachability or a live fault. Legacy active
   and inactive band-array arithmetic, including zero/unordered time paths and
   unsigned frequency conversion, is now independently decoded. Inactive attack
   and power smoothing share a coefficient; release uses its own factor. Legacy
   crossover routing also has symbolic argument/destination joins across every
   admitted band position. Conversion failures stop later work and retain earlier
   writes; single-band counts remain unused and filter histories survive.
   Arbitrary-input helper parity and allocation/lifetime remain open. The maintained
   revision and legacy contracts are linked in the HIRC graph guide.
   The packed crossover helper's tiny pair and both finite fast-vector paths
   now have direct instruction-order arithmetic proofs. The crossover wrapper's
   normalized-cutoff guard and the generator's cleared unused lanes place its
   admitted calls within that recovered domain for either selector branch.
   Original composed coefficient checks agree with independently computed helper
   returns. Other callers' large-argument reduction, exceptional handlers and
   arbitrary-input sine/cosine parity remain separate gaps.
   The band pair exception is now joined to admitted descriptor maps. It uses
   mapped parity to select an adjacent logical slot without looking up or
   checking its partner. Sparse maps can select unrelated channels, padding or
   an unsigned predecessor outside target scratch. Original finite-input kernel
   paths confirm the local arithmetic; host selection and live reachability remain
   unresolved. Descriptor admission must not be treated as pair safety.
   Remaining work is the complete IR extent/encoding and alternate kernels,
   Mastering's helper equivalence, exceptional floating behavior and allocation,
   remaining startup/constant lifetime conditions, shared-context counter meaning
   and concurrent ownership, public control names, and live selection. The later
   shared-state routine's polynomial sample blend, history capture, identity
   matching and timer arithmetic are proved under admitted storage. Its producer,
   duration calculation, unit-counter transition trigger, discontinuity reset,
   local termination and separate global cleanup are now joined. Reallocation
   writes capacity and returned pointers before success checks; allocator recovery
   remains conditional. The normal local-engine caller also joins prepared
   channel count, rounded stride, fixed local DSP rate, internal frame capacity
   and scratch requests. Refresh rejects channel-format changes. Shared transition
   duration uses the separately supplied rate. Wider standalone strides, actual
   external buffer capacity and the word-sized frame-offset wrap boundary retain
   explicit admission gaps. Primary maxima must be divisible by four, which still
   admits aligned values beyond finite traversal; complete original refresh checks
   reach their wrapping paths with downstream effects modeled. Complete local buffer setup reuses nonnull main
   pointers without checking capacity, retains earlier allocations after a later
   failure and overwrites the optional pointer on every enabled setup. Its
   request arithmetic and return paths are proved, while allocator capacity,
   retry cleanup and ownership remain conditional. Every valid old/current peak
   mode also reaches its shared delay-storage tail after coefficient writes.
   Existing delay storage is retained; only successful new storage is cleared.
   Optional side storage is requested at most once when enabled. Failures retain
   earlier writes, and initial histories reset only after successful application.
   The complete local request/return behavior is proved with helper and allocator
   models; actual capacity and ownership remain separate gaps. Band optional storage
   likewise retains existing first-channel pointers, requests once per active band
   in order and stops on failure while preserving earlier writes. Update clamps cannot constrain
   bulk-loaded values. Do not substitute corpus correlation or sampled numerical
   agreement for the missing consumer or whole-implementation proofs.
2. **Layers 5 and 6 need a host, not a reader**: link the SDK Profile libraries,
   load the game's `.pck` files through the sample file-package I/O, register
   the plug-ins the game compiles in, and use the Query API and output capture
   under chosen switch/state/RTPC values. Treat its output as a strong prior and
   cross-check the native path in [`audio_native_hooks.md`](audio_native_hooks.md).
3. **Music reach remains two bounded walks.** The WebUI builder already follows
   music containers from its broad authored Event set; the metadata-literal
   named-reach gate starts from a narrower set and still finds no music media.
   Preserve both start-set definitions when widening either walk.

## Do not repeat

- Corpus-only stride sweeps for any HIRC type: the reader that wrote the bytes is on disk.
- String-mining the game DLL, or re-deriving what these notes already record: read memory first.
- Little-endian varint decoding of HIRC fields.
- Per-package joins for anything that can land in two `.pck` files.
- Reconciling the two corpora by widening the bank regex.
- Reading the stream packages whole through the CLI JSONL stream (out of memory).

## Recipes

The SDK reading workflow (dumpbin on extracted objects, relocation-table vtable
slots, `pdb_enums.py`) lives with its dumps under
`scratch/reverse_engineering/wwise_sdk/`. The corpus gates are
`python -m scripts.webui.audio.semantics.hirc_action_corpus
--expected-input-set-sha256 <current inputSetSha256>`, then
`python -m scripts.webui.audio.semantics.hirc_named_reach`, about four minutes
each, after `scripts\game_data\extraction\animestudio\rebuild.bat -Target CLI`.
