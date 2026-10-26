# The native audio chain, and what a bounded capture would prove

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** The runtime side of the audio lane: how far the managed
external-source request is statically closed inside the selected build, which
read-only probes are prepared against it, and why none of them yet joins a key
to an opened file, a decoder stream, or audible PCM. It is the audio counterpart
of [`native_read_path.md`](native_read_path.md).

The LevelScript music compiled-call claims are a separate, limited source
lane. They freshly check named Param-field reads and ordered call sites in
`PostMusicEvent.Execute` and `OnRelease`, then the facade's call to
`AudioMusicSystem.PostMusicEvent` and that system's named mode/state helpers.
This establishes compiled call shape. It does not establish the closed Param
context's evaluated value, unchanged result transfer, selected music branch or
the eventual control, cue or Wwise sink. The public audit therefore withholds
Event-request admission even when these claims pass; source names and a music
method name never substitute for those joins.

Live capture tooling is internal-only and is excluded from the public
repository. The retained paired source bridge and owner/carrier recipes below
support historical evidence validation. The separate saved `audio source-owner`
entry-only recipe is reconstructed by `prepare_endfield_source_owner` from
authenticated source, queue and carrier contracts. Its recorded selector,
clone, wide setter, factory, constructor, embedded consumer, Lock and
carrier-control entries remain distinct from both managed post methods. Native
results and parent nesting are absent, so these rows cannot replace historical
paired recordings. The classic five-hook recipe remains a separate format.

The new `audio/source_owner.jsonl` carries bounded declared scalar reads,
one guarded descriptor, bounded terminated UTF-16 text, original register
arguments and return address. Read, guarded-out and inaccessible/unterminated
states are distinct. Result-only constructor fields are omitted and the
carrier never dereferences text or media. Its strict
`audio.semantics.source_owner_capture` audit re-proves the selected contracts,
checks the staged recipe/activation/runtime, writer and callback receipts,
paired windows and exact source-row count, and admits only local carrier
owner comparisons with reviewed callers and address points. It cannot
recreate the historical paired bridge or a cross-call lifetime join. A complete
retail native recording now admits selector, clone, wide setter, factory,
constructor, embedded consumer and Lock entry observations. Captured native
texts are counted per hook, without inferring an interval or chain. The saved
set includes source snapshots whose bit eight is set, whose data pointer is
nonzero and whose stored word eight is zero. These fields do not identify
media bytes or a live provider. No carrier-control entry was recorded in the
admitted window; this supplies no negative claim about playback or another
window. Counts and path inventories remain in generated audits. Reusable
recipe projection lives in `audio.semantics.source_observer_profile`, shared
by preparation and strict publication; production does not import capture
orchestration to reconstruct the entry recipe.

Publication re-proves the selected binaries with current native validators;
this can strengthen the explanatory exact-tier text after a recording was
made. The auditor retains both capture-time and current proof text rather
than attributing new offline checks to the recording. Only that bounded text
value may differ, with identical evidence-boundary keys. Captured ABI IDs,
read programs, hooks, file identities and every other declaration remain exact,
and the original session is never rewritten.

The `audio source-io` selection expands the observation boundary with the
provider's retained descriptor, selected I/O context and external-package
lookup path/key. A complete retail recording now admits those local reads
under independent retention and package gates. Terminated voice text occurs
in retained provider descriptors; the later start entry reads a selected
device whose I/O address point matches the reviewed default package dispatcher.
Hash entries use complete voice paths, and lookup entries receive the
corresponding computed full-width keys with the required external kind.
These are independent input cohorts, not paired calls or returned package rows.
Repeated lookup attempts include empty package tables and do not mean repeated
voice plays. No file handle, media read or decoded output is admitted.
The expanded recipe now adds the primary-provider package-completion entry
to collect its request, incoming status and existing result descriptor in the
same window. Its static gates and transparent thunk tests pass; those new
fields still require their own complete recording. Earlier recipes retain
their exact declarations and cannot retroactively supply completion fields.
Closed native windows are retained within a bounded history so delayed entries
are routed by their recorded timestamp even after the user stops the window.
Finalization quiesces logging before the last drain. A full history or ambiguous
boundary fails closed rather than silently dropping an in-window observation.

The combined `audio source-provider` selection retains the source/owner/carrier
recipe and adds decoder-provider preparation, ordinary/alternate factories,
ordinary open-dispatch and descriptor-storage entries under their own selected
native gates. It samples a local decoder-to-owner-to-source view, ordinary
descriptor input with guarded terminated text, and alternate factory arguments
without dereferencing media. The open-dispatch name identifies an observed
wrapper entry, not a successful operating-system file open. The ordinary
source-owner recording cannot supply these rows. A complete retail recording
now observes ordinary and alternate factory entries, ordinary open-dispatch
and descriptor-storage inputs. Requested voice paths occur at the ordinary
factory, open-dispatch and storage entries. The authenticated caller uses a
source-based preparation routine; the separate decoder-preparation entry was
not observed in this window. These are local entry observations, not a chain
between calls. Returned providers, completed text storage, file opening and
cross-call lifetime stay unresolved. Capture distinct representative
voices in one window to exercise branches together; no per-hook, per-character
or repeated confirmation capture is required. Reuse the whole saved recording
for later analysis before requesting another named missing branch.

Every claim here is bound to one selected `global-metadata.dat` plus the
matching `GameAssembly.dll`, supplied explicitly; missing or mismatched binaries
retain authored evidence but omit build-locked callsites, mappings and runtime
addresses. Addresses, RVAs, offsets and branch tables live in the hook catalog
[`scripts/webui/story_recovery/audio_runtime_trace_hooks.json`](../../scripts/webui/story_recovery/audio_runtime_trace_hooks.json)
and the generated audits under `reports/story/recovery/audio/`, which are static
dispatch evidence, not a playback trace. Never carry an address over from a
previous build, and do not restore module-global default game paths.

## Managed side: closed statically

- **Voice key.** `VoicePlayer` formats `("{0}/{1}/{2}", "Voice",
  VoiceI18n.s_languagePrefix, VoiceData.path)`, giving `Voice/<language>/<path>`,
  and `_PostEventWithExternalSource` passes that same string to
  `AkExternalSourceInfo.szFile` before native descriptor copying. **The
  key-to-copied-descriptor path is closed**; source-state/sourceInfo instance
  selection and opened-handle identity are not.
- **PlaySound strings hash as written.** The checked default object and position
  branches of `PlaySoundAction._DoPlaySound` pass the serialized `_soundEvent`
  untrimmed to `AudioHashGenerator.Compute(string)`, which folds ASCII case and
  keeps whitespace; the installed `IFixPatchOut` set declares no replacement for
  those methods. Validator: `native_play_sound_string.py` against
  `audio_play_sound_string_native.json`, whose docstring holds the route detail
  and the trailing-space counterexample. Other PlaySound routes, live execution,
  runtime patch state and audibility stay open; see also
  [`ifix_patch.md`](ifix_patch.md).
- **Declared codec enum and raw propagation.** `Beyond.Audio.AudioCodec`
  (`PCM=-1`, `ADPCM=1`, `VORBIS=2`, `ATRAC9=6`, `OPUS_WEM=10`) flows unchanged
  from serialized `VoiceData.codec` through `RuntimeVoiceData.codec` and the
  adapter's typed parameter into `AkExternalSourceInfo.set_idCodec`, whose export
  stores it directly in the descriptor's codec slot. The enum's named values
  differ from the public `AKCODECID_*` constants (`PCM=1`, `VORBIS=4`,
  `ATRAC9=12`, `AKOPUS_WEM=20`).
  These enum labels do not restrict the integers actually stored in
  AudioDialog. Preserve its raw values rather than translating through the
  enum names. The reviewed external selector now proves the later conversion
  into the prepared source argument, described below; the concrete game codec
  implementation remains open. The nearby sourceInfo/provider fallback field
  is a stream byte bound with no static edge from `idCodec`.
- **External Source cookie.** Every serialized External Source record carries
  the constant the VoicePlayer helper writes before `PostEventExternal`
  (recorded in `mono_behaviour.py`); that closes callback-family selection, not
  a per-request path.

## `AkSoundEngine.dll`: what the static chain closes

Read each line as *closed* (a direct static edge), *bounded* (a census with the
stated scope), or *open*.

The provider-to-file, async-read and decoder-output rows below summarize
historical static audits. The retained provider audit describes a different
Wwise image, so those rows are investigation directions rather than admitted
current-build file/read or codec claims. The selected current contracts in the
provider-preparation section below reauthenticate preparation, construction
and storage; they deliberately leave downstream file/read identity open.

| edge | status |
| --- | --- |
| external manager key generation | *bounded*: a lock-xadd serial slot, serial+1 stored on the registration record before the constructor retains it; only two direct callers of the generator, both registration/external-post bridges; both constructor wrappers covered |
| source-construction join | *closed*: the parent-B/source-state key is compared directly with the manager entry's serial, no hash transform; four join callsites, only the two construction callers carry that key |
| serial = source-state key? | *open*: no source-state writer stores from the serial slot and the serial global has no direct read at the constructors -- negative direct-call evidence only, not proof against indirect aliasing |
| source config / metadata producers | *closed* direct producer and local field reuse: one direct source-config entry reads parent B's key field; parent B is not aliased to the registration record; the metadata pointer has no edge to the manager's descriptor allocation |
| copied descriptor on the manager entry | *closed*: an ownership-retention field (0x14-byte payload copied, first qword stored), read only for refcount release on detach; not a path, provider or codec input |
| exact join hit | *closed*: appends the source-state pointer to the entry's attachment array; lifecycle only, no media selection |
| sourceInfo word | *bounded*: an internal selection key through its own global slot (distinct from the manager hash slot and the decoder registry), joined into source/provider setup |
| sourceInfo to provider | *closed*: with flag bit 9 the descriptor's UTF-16 path goes through the singleton provider vtable into provider storage; the call carries no manager entry or key |
| provider to file | *closed* transport: the default-I/O first slot reaches `CreateFileW`/`GetFileSize`, storing handle and size; the path helper picks the incoming path or the device base path |
| pump to `ReadFileEx` to request recycle | *closed* into one codec provider allocation (primary vtable at the base, secondary interface to the decoder); callback ownership stays upstream; the candidate-carrier source is a *conditional* edge |
| provider to decoder | *closed*: refill passes the provider buffer to the decoder, which stores it; refill/reset release through the provider |
| decode output | *closed*: float samples scaled and written as signed PCM16 to the caller's buffer |
| stream setup | *bounded*: exactly two direct setup calls (Opus wrapper, generic memory wrapper with a copy/seek/data/free descriptor); no in-image static pointer to setup or the codec callback; runtime-computed pointers open |
| decoder callers / callback readers | *bounded*: three direct decoder callers (PCM16 writer, initial attempt, retry after refill); ten codec-callback readers in seven functions; parser callbacks are integer-array transforms, not PCM sinks |
| optional decoder callback context | *bounded negative*: read once, no direct store in the surrounding window; indirect initialization not excluded |
| manager constructor status | *closed*: decoded success versus allocation-failure return (surfaced as `registrationStatuses`); status alone proves no source-state, file or PCM identity |
| source-manager / exact-key callback branches | *closed* as callback-descriptor and notification transport only |

What no static reading supplies: a **live** key-to-provider invocation, the
runtime source-state/sourceInfo identity, the remaining address-taken codec
callback targets, and callback ownership.

## Prepared probes and what the importer may claim

The hook catalog verifies `AkSoundEngine.dll` and holds managed external-post
and callback boundaries plus native lookup, key-join, key-to-decoder registry,
source/provider preparation, descriptor-copy, callback-queue, Wwise open and
async-read probes. **They are prepared evidence only until an authorized
capture observes a match.** The relations the importer publishes and the
ceiling on each (keys, manager-entry pointers, descriptor retention, synchronous
nesting, managed-to-native path lifecycle, callback transport, open-handle into
`ReadFileEx`, decoder-entry continuity) are documented in
`scripts/webui/story_recovery/runtime_trace_audio_import.py`. None of them is a
handle, decoder-stream, PCM or audibility join by itself.

**Re-pinning is gated per half** (`python -m
scripts.webui.story_recovery.refresh_audio_hook_catalog`; detail in its
docstring). Managed hooks in `GameAssembly.dll` move with every client update
and are re-resolved by name. Native hooks in a rebuilt `AkSoundEngine.dll` may
not move; each activated RVA must land on a `.pdata` function start or the
manifest is refused. The capture host, not this repository, converts the
catalog into its activation manifest. Only the five host-required hooks are
refreshed; the other rows keep superseded addresses and are not evidence for
the current build.

## What gated sessions have shown

`scripts/webui/audio/semantics/runtime_capture_import.py` validates a session
against the provider's own completeness counters and decodes the writer's
208-byte `AudioEventPayload`; its docstring records the findings:

- **A capture cannot name an Event.** The hooked post carries the hash, never
  the spelling.
- Posted Events include ones with no recovered name, so hash-only Events are
  genuinely used.
- **The managed scalar is an Event ID, not an external cookie or package key.**
  The adapter records Event ID and audio object ID at entry and retains the
  external-path string. One Event ID can accompany several paths. Earlier
  importer `sourceKey` labels were incorrect; the corrected importer names
  this scalar `eventId` and advances its report schema.
- The source-owner auditor's independent
  [`managed request summary`](../../scripts/webui/audio/semantics/managed_post_observations.py)
  checks the recipe hook index, retained text, nesting and paired result.
  It reports the returned playing ID and raw callback-type argument without
  joining asynchronous native entries. Lossy, missing and bounded text stays
  separate from complete ASCII projections. Nonzero playing IDs do not prove
  decoding or audibility; historical external cookie and codec arguments were
  not recorded.
The selected source gate now checks complete ordered managed signatures through
registered IL2CPP runtime types, not only a metadata-rendered parameter prefix.
It verifies staticness, return type and enum classification/backing fields;
hidden `MethodInfo` is separate from the managed parameter count. Callback type
uses signed integer storage and the raw Beyond codec argument unsigned storage.
That storage proof does not equate Beyond enum values with Wwise codec IDs.
- Only banks are opened through `DefaultIoOpenDispatch`, each probed across the
  Persistent/StreamingAssets and `Chinese` overlay order of
  [`../game_data_recovery.md`](../game_data_recovery.md); voice media is read by
  a path these hooks do not see.

## Codec selection and the remaining output gap

Historical SDK symbol matching (`scripts/game_data/wwise_sdk_symbols.py`, rows
annotated on every re-pin) identified three source families: `CAkSrcFileBase` /
`CAkSrcFileOpus` (Opus streamed from a file), `CAkSrcBankVorbis` (Vorbis
resident in a bank or prepared media, no stream), and `CAkSrcMedia` with
`CAkSrcMediaCodecVorbis`/`PCM` (the media-source interface). The catalog's
three codec rows are the Opus file path and were never enabled. The historical
`SourceProviderPreparation` correspondence was `CAkSrcFileBase::CreateStream`;
its absence during a recorded voice window is not a negative playback or
file-opening claim. The current selected-byte factory proof supplies a
conditional family choice independently of these historical SDK labels.

The reviewed
[`wwise_source_native.json`](../../scripts/game_data/contracts/wwise_source_native.json)
validates the selected installed inputs for the source/owner, decoder/provider,
codec-factory, voice/routing, authored-parameter, inheritance, sink, playback,
bus-processing and RoomVerb declaration families. Shared rules for all of them:

- Re-derived witnesses follow current callers, constructor-installed address
  points and registry records; register allocation, stack storage and compiler
  inlining are not identities. Named direct-memory calls and helper
  replacements need their own complete field, argument, control and return
  proofs. Native coordinates and instruction programs stay in the contracts.
- The owner/carrier command dispatcher requires an unsigned bounded index, the
  matching table load, module-base addition and terminal dispatch. Queue serials
  describe batching; entry-only cleanup never licenses a return-time pointee
  read. Authored property maps keep byte-key and word-key loops separate. Sink
  format selection binds the current speaker-mask helper to its packed caller
  configuration.
- Bus-processing expressions are derived from the selected SSE/AVX programs;
  private-buffer kernel comparisons establish only those bounded expressions,
  and historical numeric results cannot substitute for current programs.
  RoomVerb declarations bind tone, diffusion, feedback, lifecycle and parameter
  ownership without establishing live selection or whole audio output.
- Historical PCM, prepared-output, bus-sum, matrix, modeled-COM, impulse,
  registry and lifecycle cohorts retain their original-build scope. Static gates
  and offline forwarding/unwind checks establish no current live ownership,
  allocation generation or audibility; a manifest that prepares successfully is
  not a current execution result.
- Offline cohorts execute original native code under explicitly supplied
  conditions (allocators, COM/endpoint responses, worker dispatch, registry and
  topology state). They are *conditional* computations, never observations of
  the game's scheduling, live pointer generation or device output, and helper
  failures under invalid supplied state are not game defects.

### Static and offline chain, by owner

Each row is the current conclusion; the module docstring's "Evidence and
admission boundary" holds the route detail, supplied conditions and withheld
branches.

| stage | owner | current conclusion |
| --- | --- | --- |
| source ABI | [`wwise_source_native.py`](../../scripts/game_data/wwise_source_native.py) | `SetSource` overloads and `LockDataPtr` authenticated; a strictly audited returnsite pair gives a *conditional* owner/source/output relation; constructor and factory transport an already-selected source pointer. External cookie, SetSource scalar and lookup word are not interchangeable; the retained source argument stays anonymous. |
| queue and selection | [`wwise_source_queue_native.py`](../../scripts/game_data/wwise_source_queue_native.py) | Descriptor retained through event queue into the Action argument blob; posted Event ID resolved by full-DWORD registry match; Event→Action list order is *conditional* (distinct Actions, no later link mutation); Play Action target lookup has no namespace fallback. The bank source ID is the descriptor cookie, not a package key. The selector takes the first usable descriptor in stored order (no path choice from the Event ID alone), and preparation may replace the match word, so a source snapshot need not retain its cookie. The prepared source argument is the raw codec value's low halfword moved to the high halfword plus the codec-kind tag, not a managed enum translation. Bank loader takes a fifth Win64 stack-byte argument. |
| playable-file provenance | [`package_decode_witness.py`](../../scripts/webui/audio/semantics/package_decode_witness.py), [`wwise_package.py`](../../scripts/game_data/wwise_package.py), [`hirc_v150.py`](../../scripts/webui/audio/semantics/hirc_v150.py) | Physical bank Event → Play Action → Sound → external or numeric package row decodes to exactly the existing voice/WEM PCM, Vorbis and Opus. Stream type is buffering policy, not media location; a numeric media ID alone is not physical file identity. Authored provenance only. |
| codec construction | [`wwise_codec_factory_native.py`](../../scripts/game_data/wwise_codec_factory_native.py) | Plugin registry first match wins; Vorbis and Opus share the media wrapper with distinct codec instances. The RIFF reader is not a safe arbitrary decoder. Original native codec execution reproduces the offline PCM (isolated helper: exact floats). Duplicate IDs: lookup picks the greatest byte count, ties the first list occurrence. Memory-labelled sources use the resident-memory branch though their WEM lives in a sound package. Registry ID and numeric file ID stay distinct. |
| package lookup and load | [`wwise_external_package_native.py`](../../scripts/game_data/wwise_external_package_native.py) | Numeric lookup compares key/language pairs; bank codec classes do not fall through to the sound table; packages searched in list order, first success wins; load prepends, the package-ID routine moves a match to the head. Original header load and media XOR yield the maintained reader's tables and the exact clear WEM. |
| standard stream | [`wwise_standard_stream_native.py`](../../scripts/game_data/wwise_standard_stream_native.py) | Original factory, `ReadFileEx` reads and completion feed resident memory, provider and context PCM. A short OS read is **not reconciled** by the completion chain: admission must keep actual OS counts and full encoded/clear hashes. |
| owner, frame, sink | [`wwise_voice_pipeline_native.py`](../../scripts/game_data/wwise_voice_pipeline_native.py) | The former "owner readiness" is a parameter refresh whose result is ignored. Attachment success does not imply preparation or PCM. Frame preparation removes a leading-silence quantum; frame release is mandatory. The steady-state sink ignores the `ReleaseBuffer` HRESULT, so buffer contents alone never prove OS acceptance. |
| routing and bus mix | [`wwise_voice_routing_native.py`](../../scripts/game_data/wwise_voice_routing_native.py) | Gain refresh must precede route preparation; the bus allocation is built from native route rows; bus frame reset is required. Logical sample values match the decoder; signed-zero bit differences are recorded separately. |
| sink negotiation | [`wwise_sink_negotiation_native.py`](../../scripts/game_data/wwise_sink_negotiation_native.py) | Shared-mode, event-callback negotiation with Windows auto-conversion first and a native resampler fallback (its output unproved). Stream category is a conditional interface call, not a voice-family endpoint mapping. |
| authored parameters | [`wwise_authored_parameters_native.py`](../../scripts/game_data/wwise_authored_parameters_native.py) | Fixed properties reach mapped native slots by consumer read; authored gain and low-pass change submitted PCM consistent with the AVX/FMA reconstruction. Padding precedes filtering, so a padded tail need not be silent. The own-Sound cohort has an unlinked parent. |
| inheritance | [`wwise_inheritance_native.py`](../../scripts/game_data/wwise_inheritance_native.py) | Registry membership and child-first load order are consumer preconditions; STMG framing feeds defaults before hierarchy load; inherited collection composes with the full PCM chain. Listener component uses the original lazy default on a null component. |

Net: offline native computation is *conditional* from physical package bytes
through codec, route mix and a negotiated finite render buffer. Game
scheduling, effective authored topology and effects, a real endpoint and
audibility remain open.

### Live phase captures

Saved source-entry profiles lack component/listener selection, later frame and
mixer reads and output completion; replaying them cannot recover those phases.
The concrete capture requirement lives in
[`runtime_capture_requirements.md`](../runtime_capture_requirements.md#audio-event-owner-listener-and-output-selection).
Each preset has a reviewed capture contract and an Audio semantics domain whose
docstring holds its admission rules:

| preset / review | owner | admitted result |
| --- | --- | --- |
| `audio-playback` | [`playback_capture.py`](../../scripts/webui/audio/semantics/playback_capture.py) | Default and held-component getter calls, nonempty listener selection, finite source PCM prefixes and normal sink returns. Selector playback serials match managed Event return IDs; one Event can retain several source words. Package low-word matches are candidates only. |
| live PCM identity | [`playback_pcm_witness.py`](../../scripts/webui/audio/semantics/playback_pcm_witness.py) | A finite nonzero live voice PCM prefix exactly matches original native codec output from the matching package WEM: sampled content agreement, not live buffer, allocation generation or backing occurrence. |
| `audio-device` | [`device_capture.py`](../../scripts/webui/audio/semantics/device_capture.py) | Same-sink, same-client `GetBuffer`/`ReleaseBuffer` succeed and the copied bytes equal sampled sink input (matched stereo only). Individual Event contribution to a mixed device frame stays unresolved. |
| `audio-mixer` | [`mixer_capture.py`](../../scripts/webui/audio/semantics/mixer_capture.py) | `busRouteMix`'s fourth argument is a mixer-row array, not routes; older route-array labels are withdrawn. The old owner-ID read hit a neighbouring word; corrected current serials have managed Event candidates and some full owner/serial/source/allocation tuples. Stored identity is non-atomic. |
| mixer frame | [`mixer_frame_capture.py`](../../scripts/webui/audio/semantics/mixer_frame_capture.py) | Publication reads the same current identity as sampled PCM; source and bus-output prefixes differ, so pointer continuity is not an unchanged copy. The numeric session was lossy and withholds interval joins; the unchanged repeat is withdrawn. |
| bounded mix equation | [`mixer_pcm_witness.py`](../../scripts/webui/audio/semantics/mixer_pcm_witness.py) | Evaluates a constant first-output equation; an evaluator regression, not a live consumer observation. |
| `audio-handoff` | [`sink_handoff_capture.py`](../../scripts/webui/audio/semantics/sink_handoff_capture.py) | Both saved frame recipes fail the write/consume coverage gate. The handoff capture links a completed master conversion's prefix to a successful render-client submission through checked write/submit IDs. |
| `audio-mixer-consumer` | [`mixer_consumer_capture.py`](../../scripts/webui/audio/semantics/mixer_consumer_capture.py) | Live numerical agreement at the original matrix consumer up to parent bus output for the admitted cases, with the full Event/source/file tuple. |
| `audio-master-stage` | [`master_gain_witness.py`](../../scripts/webui/audio/semantics/master_gain_witness.py) | Retained master gains are unity; prefix differences already exist at master entry, so they precede this stage. |

Open across all captures: whole buffers, unobserved writers, concurrent
allocation lifetime, all channels/filters and an individual Event's
contribution to the device mix. The next offline review is the post-mix bus
task and descriptor/effect processing into master entry, before another recipe
is requested; accepted captures are reused, never repeated unchanged.

### Shared post-mix processing patterns

[`wwise_bus_processing_native.json`](../../scripts/game_data/contracts/wwise_bus_processing_native.json)
records complete output-task, post-mix, effect-consume and effect-dispatch bodies,
borrowing the existing planar frame-gain and master-output owners. The selected
task collects bus input, then its synchronous branch prepares the bus before
optional master output. Deferred task results are a distinct branch; returning
the caller's result storage is not voice readiness or device submission.

Descriptor-owner gains can represent pending arithmetic rather than gain already
present in PCM. Under the ordinary effect-entry prepass, non-unity previous and
target gains are applied through the original frame-gain routine, then both
retained words are set to unity before effect execution. A suppression flag
skips that prepass. Thus unity at a later master entry does not mean upstream
gain was absent. The original routine executes offline on complete private
planar buffers and agrees in supplied constant-gain, suppression and control-
transition cases. Private vtable callbacks supply effect arithmetic and reset;
this proves engine ordering and gain/control behavior, not a game effect kernel.

The shared effect driver separates in-place, separate-output and multi-object
paths. In-place execution receives existing descriptors; separate-output paths
can replace the selected descriptor collection. Current/previous control words
also govern execution and reset, so descriptor presence alone does not imply an
effect ran. Track the selected collection, descriptor, owner, PCM and method
target through the actual branch instead of flattening this into one permanent
buffer pointer or assigning a public SDK class name from proximity.

The first bus-processing recording expanded every bus task and saturated its
queue. It is excluded from complete processing/master/device joins. The offline
reader also hit report-row limits; those limits now cap retained witnesses while
continuing phase pairing and counting, with explicit truncation diagnostics.
The corrected bus-processing observer samples roots by their declared task index
and forces all mix, matrix-consumer, post-processing, effect, frame-gain, EQ
instance, biquad-service and master descendants of each selected root. Job storage is reused across indices,
so its pointer is not a valid sampling key. Unselected roots and their scoped
descendants remain unobserved; this proves no global bus or allocation coverage.
The frame-gain ABI
has floating operands; its wrapper preserves them and records their bit words
and entry rounding. Guarded field-based pointer reads retain the actual first
effect object's vtable and Execute target without extending an unbounded
pointer walk. The offline consumer requires native return sites, same-task
nesting, preserved storage/owner fields and prefix continuity on both sides of
post-processing; only its admitted master invocation may join the existing
sink/device chain. Gain arithmetic, reset-to-unity and residual effect-prefix
changes remain separate claims. Missing task selection, late/unwound pairs,
bad addresses, loss or diagnostics withhold publication. Full buffers, changing
gain arithmetic, general effect parameters/state, allocation generations,
concurrent writers and individual Event contribution remain open. A clean scoped
recording now admits the selected mix-return/post-processing/master/device
prefix chain. Reuse that accepted branch without repeating it. The earlier
master recording remains accepted, while the expanded all-root bus attempt is
retained as local investigation evidence only.

The same contract now records direct registration/factory/constructed-vtable/
Execute joins for Parametric EQ and Compressor. The named parameter-schema owner
remains `wwise_effect_parameters_native.json`; its selected native inputs and
named parameter bodies are checked without duplicating its catalog. Paired
runtime vtable and method-pointer observations match those constructed tables.
Bounded lossy task examples locate prefix changes at the EQ driver and unity
frame-gain calls inside the later Compressor. These local observations guide
recovery; they do not admit a complete task/device chain through a lossy stream.

The Compressor collection path suppresses the shared driver's gain prepass and
performs its own pending owner-gain materialization. It can then publish new
previous/target makeup gains into identified descriptor owners instead of
changing PCM immediately. Sentinel owners, or LFE exclusion requiring a
channel-specific operation, take an inline PCM path; including LFE allows the
uniform gain to remain deferred. Complete private-buffer executions of the
original kernel validate controlled deferred, inline, zero and LFE cases. The
detector operands in these trials suppress detector gain changes; general
compression arithmetic, live controls and state are not established. A unity
word after this kernel is not automatically a driver reset-to-unity claim.

The EQ driver maintains three enabled bands, refreshes their coefficients and
dispatches their processing through a runtime processor interface. Its history
lookup combines the owner identity and channel, rather than using a PCM pointer
as the persistent key. The reviewed collection processor locates independent
history storage for that key. Thus source PCM and one gain value do not suffice
to reproduce a stateful bus effect: coefficients, enabled branches, processor
selection and the correct history are additional inputs. The reviewed service
dispatch selects authenticated SSE or AVX processing; a uniform segment takes
the corresponding uniform kernel. Original execution on complete private
buffers confirms the service ABI and agrees with each selected uniform kernel.
Changing later input and the other buffer leaves the first output prefix
unchanged, while changing initial history or coefficients changes it. SSE and
AVX can differ in their last float bit, so processor selection and entry MXCSR
are required operands. This establishes the scope needed for a bounded live
comparison, not a replay of a captured game effect.

The prepared observer records the actual EQ instance and its newly constructed
collection, output-gain controls, enabled-band flags and processor implementation.
The shared driver originally receives a descriptor-base/count collection; its
multi-object branch constructs a distinct count/descriptor-pointer-array/owner-
pointer-array collection for EQ. A pointer-equality join between those two
representations is invalid. The reader instead requires the same instance,
descriptor, owner-array entry, PCM and properly nested call identities. Inside
that admitted instance it retains each original service invocation's first-buffer
PCM prefix, coefficients, initial/returned history and processing geometry.
Sequential service prefixes must connect without gaps. The last service prefix
and final effect prefix remain separate because EQ output gain may also run.
The selected native contract now carries separate first-block SSE and AVX
expression programs, with complete kernel, dispatch/caller, instruction-path
and constant provenance. The portable evaluator uses integer dyadics, retaining
one binary32 rounding per SSE operation and one rounding per AVX fused operation.
Controlled original-kernel trials match its first-buffer prefixes bit-for-bit,
including zero, identity and impulse inputs. The admitted normal finite range
requires nearest rounding and masked exceptions; unsupported subnormal or
range behavior stays explicit. A textbook scalar recurrence is insufficient
for exact parity with the binary's optimized block arithmetic.

The original kernels' controlled initial-history responses and returned state
establish the history order as the prior two output samples followed by the
prior two input samples, each older sample first. Capturing returned history
does not explain its full transition from only an input prefix: that needs the
remaining input frame. The live reader reports per-service numerical results
and separately counts exact nonzero results within device-linked tasks; an
operand chain alone is not numerical admission. A clean live recording now
confirms the observed active EQ-band sequence under the selected AVX branch:
saved coefficients, initial history and entry rounding reproduce each checked
first-buffer prefix bit-for-bit. Sequential band prefixes connect, the final
EQ prefix equals the effect return, and those completed tasks join master
conversion and device submission. This is conditional numerical admission of
the checked mixed-bus prefixes. The live case separates unity master-input gain
from a later non-unity sink-conversion gain before byte-equal render-client
copies; those are independent amplitude stages. Live SSE selection, unsupported segmentation,
other channels and whole-buffer output remain unresolved.
A bounded positive reader example covers
the task/EQ/master/device join; wrong ownership, processor targets, addresses,
operands or nesting cannot supply an EQ operand claim. This native consumer recovery
does not rename the anonymous stored parameter partitions or prove their public
control units.

EQ output gain also uses pending owner arithmetic. When LFE inclusion permits a
uniform operation, it multiplies identified owners' previous/target gains and
can leave PCM unchanged. LFE exclusion takes a direct per-channel path, with
an excluded LFE plane preserved; the EQ instance updates its previous-output-
gain state after either branch. Original complete-private-buffer trials with
disabled bands distinguish deferred gain, inline ramps and the unity no-op.
These supplied-control trials do not admit a live gain ramp or power-helper
equation. Thus a matching last-biquad and final-effect prefix can coexist with
an effect that changes later output through retained owner gains.

In the accepted live branch, EQ output gain is unity. A middle driver slot has
empty object-collection snapshots and unchanged PCM; it is not an unidentified
effect kernel. The following registered Compressor materializes unity owner
gain and adds no further change to the checked prefix. This does not prove
general compression or non-unity effect-gain behavior. Guarded failed biquad
operand reads occur in zero-buffer calls, outside the admitted stereo service
branch; they cannot supply DSP operands or undermine the separately complete
selected chains.

The admitted master input already mixes multiple source rows. Earlier singleton
source-to-consumer candidates cannot explain an individual contribution through
that mix. The original AVX matrix consumer expands source channels and calls
separate constant and ramp accumulators. Their first pointer is the destination,
the second the source; each lane uses fused source-times-coefficient plus the
existing destination. A ramp separately forms its first coefficient with one
step, then advances by one step per sample. Complete private-buffer comparisons
establish these first-prefix operations, including nonzero initial output and
independence from unrecorded tails. Reviewed provenance and mixed floating ABI
declarations are owned by
[`wwise_mix_contributions_native.json`](../../scripts/game_data/contracts/wwise_mix_contributions_native.json),
which borrows complete bodies from the authored-parameter contract.

The contribution recipe preserves independent output-descriptor reads for
multi-source cohorts while retaining the singleton gate on older source/matrix
reads. Its reader requires exact additions, unchanged source prefixes, original
consumer output geometry and normal return, ordered destination continuity,
completed mix output and the already admitted task/device path. Event/file
candidates additionally require matching sample/publication content and observed
owner/source/serial/allocation transport. A clean live recording now admits both
constant and ramp additions bit-for-bit, including nonzero existing destination
values. Ordered additions reach the original multi-source consumer return and
mixed output; selected master mixes then traverse the independently checked EQ
and device path. Effective per-channel coefficients and their native ramp order
are observed behavior, rather than inferred authored controls. Direct source/
Event candidates occur in earlier mixing stages: master inputs are intermediate
bus buffers. Allocation generations, every cohort member, filtered and SSE paths,
whole buffers and attribution through nonlinear effects stay open. An unchanged
accumulator or EQ repeat is unnecessary.

Intermediate buses can also be joined conditionally: a completed task's mixed
prefix enters post-processing, its stable returned descriptor/sample/owner and
content become a later actual accumulator input, and the later mix reaches the
admitted master/device path. Observed reset, replacement mix and subsequent
writers invalidate future reads of that snapshot. A later frame-gain writer
does not erase an independently admitted earlier master/device endpoint, but
that older snapshot cannot identify a future bus read. These joins use actual
same-thread call order and content, not stored routing ancestry or pointer
proximity. Ordinary Event/source candidates now traverse such intermediate
buses. Their selector source IDs have typed sound-sector candidates in current
package headers; this is not a live file-handle or encoded-occurrence selection.
An isolated Event's arithmetic through processing remains unresolved.

The intermediate changed prefixes include the registered RoomVerb instance.
Its registration, factory-created vtable and Execute slot are proved by
[`wwise_bus_processing_native.json`](../../scripts/game_data/contracts/wwise_bus_processing_native.json),
beside the existing named parameter schema. The original stereo worker calls a
three-buffer SSE blend: dry/output plus two wet inputs, each with a previous and
target gain. Products and sums round separately; transitions start at the
previous gain and advance once per sample. This differs from the matrix
accumulator's fused arithmetic and first-step convention. Original private
kernel comparisons establish the bounded blend model; the saved contribution
recipe did not record these wet inputs or gains. The reviewed
[`wwise_room_blend_native.json`](../../scripts/game_data/contracts/wwise_room_blend_native.json)
owns the dispatch, complete bodies, ten-argument ABI and new operands.
The Room observer must identify the actual registered effect object, check
nested blend callers and ordered prefixes, then require normal Room and effect
returns before attaching an admitted bus node. Wet-buffer delay/filter/feedback
generation, full reverb history and nonlinear Event attribution remain open.

The accepted Room recording now compares the original constant dry/wet sums
bit-for-bit, including nonzero wet operands. Ordered first-plane blends preserve
the normal Room and effect return, then the same admitted bus-processing node.
Some of these nodes lie on conditional Event/source-to-device paths. Every
observed gain pair is constant here: private transition examples do not become
live transition evidence. Original caller order separates the first dry-plus-
wet operation from a following unity-dry addition of two further wet buffers;
the right-channel calls exchange the two wet coefficients. This explains the
checked final blend, not how its wet samples were generated.

Zero valid input at Room entry is a separate observed case: the instance returns
a full output frame and invokes the same blend services. Driver sample/owner
reads are intentionally gated out for that initial extent. The reader admits
per-call arithmetic from the actual registered object, selected descriptor and
Room-owned sample pointer, but it does not invent the missing original input
prefix or owner. These calls cannot supply the full-input Room/effect/bus chain.
Their first dry prefix before the initial blend is zero; nonzero wet output
demonstrates why
zero current input is insufficient to infer silent effect output. The exact
delay/history origin and native tail-control selection remain separate.

The reviewed
[`wwise_room_input_native.json`](../../scripts/game_data/contracts/wwise_room_input_native.json)
and its selected-image validator prove the earlier stereo input path. The fold
clears its mono destination, normalizes the two ordinary stereo channels by the
square root of one half, and separately rounds each product/addition. Input
preparation can then run conditional tone processing. Original private-buffer
comparisons establish this fold and the tone-disabled preparation branch.
The named serialized tone-enable byte is transported by the reviewed parameter
bulk loader into the same member read by that conditional input-filter branch.
The input contract checks its complete owned parameter body and read/store
operands; recorded controls still do not prove a live bulk-loader invocation
or an atomic parameter version.
The following circular services read old history into output, replace those
ring positions with incoming samples, and advance/wrap the stored index; one
service writes a separate output and another exchanges samples in place.
Complete private comparisons cover partial spans, wrapping and repeated wraps.
The native stereo worker processes bounded blocks, retaining the source-frame
offset, and uses separate ring states for the initial copy/swap paths. Zero
length selects a different branch, so an absent delay call is not itself a
bypass witness. Reviewed branch-field operands stay in that contract.

The accepted input recording observes the actual preparation/fold and both circular service
phases within the registered Room instance. Indexed source reads retain the
current block offset; circular reads retain the actual length/index and wrap
each sampled address. It compares observed history to returned output and
checks index progression. Delay-length and optional-tone snapshots distinguish
the stored branch controls, while ordered preparation/delay prefixes remain
conditional observations. This still does not reconstruct the ring's complete
history, ER tap generation, diffusion/feedback network, full buffers or an
isolated Event's wet contribution. The stereo fold and observed old-history
outputs now reproduce live sampled values exactly, with returned ring indices
matching progression. Preparation output enters the initial copy and in-place
delay services by actual pointer, same-Room order and matching content. Some
preparation prefixes differ from the fold while tone processing is enabled;
their tone arithmetic remains unproved in that recording. The tone-byte address
is validated against the independently observed enclosing parameter-object
pointer, rather than treating the byte as an inline Room member. Zero-input
Room entries retain zero folded prefixes and nonzero history output separately
from the full-input effect/bus chain.

The next native history owner,
[`wwise_room_history_native.json`](../../scripts/game_data/contracts/wwise_room_history_native.json),
proves a separate expanded-matrix tone kernel used for input and early wet
processing, plus the stereo worker's fixed serial diffusion loop. These are
different services from the previously admitted collection EQ. The tone kernel
uses captured mono samples, an expanded coefficient matrix and previous input/
output history with separate products and sums. Each diffusion stage stores a
pair of old delayed input and output: current output is the separately rounded
sum of old input and gain times current input minus old output. It replaces the
pair with current input/output and advances the ring index. Complete private
owned-buffer comparisons establish both operations, including wrapping and
repeated wraps, without initializing the engine. They do not establish live
tone coefficients, diffusion history or full reverb parity. The history probe
records those missing operands and admits only actual registered Room nesting,
native caller/instance-owned state and checked ordered prefixes. Late feedback,
ER tap generation and late feedback are covered by the wet owner below;
isolated Event attribution remains open.

The accepted history recording now replays the input tone and serial diffusion
prefixes exactly. Ordered input-fold/tone/preparation returns are retained, as
are delay-to-diffusion and consecutive diffusion prefix candidates. It also
records the later post-diffusion tone caller. That complete preparation body
and both direct call sites are now included in the same native owner, so its
existing operands are replayed without a new recording. Captured flush-to-zero
handling explains tiny intermediate results near the reverb tail; the portable
model applies the recorded control at each separate operation, including DAZ
when observed. Original private comparisons cover these policies and retain an
explicit unsupported boundary for gradual denormal inputs. Some admitted Room
returns still join a conditional Event/source-to-device path; these remain
mixed signal observations rather than isolated Event contributions.

The remaining wet-generation owner is
[`wwise_room_wet_native.json`](../../scripts/game_data/contracts/wwise_room_wet_native.json).
Early reflections read one circular input history through separate stereo tap
weights and indices. Current input is written before tap reads, so a tap can
consume freshly written input instead of the entry history. The late service
uses independent delay rings and per-ring damped history, then combines and
rotates filtered values through a feedback sum while accumulating a wet output.
The following stateful wet damping uses the actual floating gain, previous
scaled input, previous output and pole. Complete private original-buffer
comparisons establish the selected vector operations, wrapping, full tap banks,
feedback state and damping. The accepted wet recording now reproduces every
selected early-reflection, feedback and damping prefix from its original live
operands. The early-state byte is a nonzero gate, not a canonical boolean;
requiring exactly one rejected valid stereo calls. The worker also uses that
byte in scratch allocation. The native contract records the direct zero test,
and the reader accepts only a captured nonzero byte with the original owned
early object and stable metadata at normal Room return.

The stereo worker alternates configured FDN instances into two accumulators.
Each FDN filters four delayed values, applies the feedback rotation and adds
to its accumulator; the following damping transforms each accumulated plane.
Ordered chains require every configured instance in its channel, an initial
zero prefix, exact preceding/next destination content, original pointers,
matching frame counts and call order. Both damped late planes and generated
early planes then supply the original Room blends. A tone stage, when selected,
must preserve the same ordered producer/content evidence. Failed writers
invalidate earlier candidates; truncated reports withhold chains. Actual
network/tap counts are configuration observations, not universal constants.

Ring headroom selects a vector loop and scalar remainder. Their addition
orders differ: the scalar output uses signed pairwise sums before adding the
destination, and its feedback scales each filtered value before summing and
injecting input. The first sampled values now replay both paths, including
boundary wrapping, from existing captured ring operands. Complete private
original-buffer examples check output, all rings, indices and final filter
history across these boundaries. The early-reflection prefix still selects
its vector path. These bounded joins explain sampled wet generation into the
accepted Room/effect/bus path; they do not reconstruct complete live histories
or isolate an Event. Authored coefficient generation, early scalar/remainder
paths, whole live buffers, live file occurrence selection and audibility remain
open. Reuse the accepted wet recording instead of repeating its recipe.

The history owner also proves one authored configuration link offline. The
existing Room parameter bulk loader copies the serialized diffusion control
into the parameter object. The complete refresh consumer compares its cached
value, applies a separately rounded scale and decreasing thresholds, clamps
each result between positive zero and the native maximum, and writes the gain
of each serial diffusion state. Its constants, transport instructions and
complete consumer body are authenticated in the same history contract, without
duplicating the parameter owner's native catalog. Owned original-loader/refresh
examples cover control boundaries and out-of-range values with all other
cached settings equal; only the selected gain bytes and refresh flag change.
This closes the conditional authored-control-to-diffusion-gain calculation.
It does not identify a live instance's authored effect occurrence or establish
complete initialization, tap/FDN/tone coefficient generation or update lifetime.

The separate
[`wwise_room_configuration_native.json`](../../scripts/game_data/contracts/wwise_room_configuration_native.json)
now authenticates the original registered effect's initialize/reset/terminate
slots, complete configuration/rebuild consumers and the bounded parameter
store extent. The existing parameter owner supplies its factory, vtable and
bulk-loader identity; those native catalogs are borrowed rather than copied.
The original factory and parameter loader, effect initialization, complete
standard-stereo impulse processing and termination execute offline with bounded
owned ordinary/aligned allocators, without initializing the Wwise engine.
Provided parameter examples exercise different network counts, tap patterns
and tone choices. All resources are released by the original termination path.

Reset clears delay samples and filter history while preserving ring cursors
and early-reflection phase state. Consequently a repeated impulse after Reset
can differ bit-for-bit when vector/scalar segment boundaries move. In an
explicit owned-buffer experiment, restoring the prior cursors and critical tap
indices after normal Reset reproduces the complete output. Do not reinterpret
Reset as fresh initialization or discard live phase when reconstructing state.

The reusable original configuration host can initialize directly from a
provided stored parameter projection and sample rate, then return delay
lengths, feedback filter coefficients, early weights/phase, diffusion settings,
damping pole and tone matrix candidates. The private original copy must match
the explicitly selected native inputs; unreadable/drifted inputs and unsupported
settings withhold computation. Reads and allocators remain bounded and owned.
The loss-free configuration recording now supplies the actual registered live
parameter object and sample rate at normal paired Room entry/return. Native
bulk-store witnesses define the compared setting bytes; vtable addresses,
padding and transient refresh flags are separate. The original owned host
reproduces the admitted network lengths/filter coefficients, early bank gains
and phase, diffusion lengths/gains, wet damping pole, input copy/swap delay
lengths and stage-specific tone matrix candidates exactly. The configuration
reader and native validator own this comparison; the generated
[`configuration admission`](../../reports/audio/room_configuration_admission_065550824.json)
retains its sampled coverage and exclusions.

The first tone comparison used an assumed input insertion enum. Instruction
review proves separate native selectors for input, early stereo and late tone;
the configuration contract borrows those complete consumers and validates each
selector operand. Correcting the input selector makes the saved matrices match,
without another capture or an arithmetic tolerance. Tone equality remains a
candidate among matching same-stage slots, not a unique allocation join.

Known settings can remain equal while the effect replaces its network and
early-history allocations inside a Room call. The accepted recording contains
such a replacement with consumed refresh/rebuild flags. The complete Execute
body tests those flags before processing; paired observations are consistent
with that native route, but do not prove atomic settings or an update
transaction. Wet ownership checks correctly withhold the stronger state/bus
attachment for the replacement call. Do not promote matching configuration
values into continuous live history.

Bounded single-control original initialization examples around the admitted
settings distinguish delay geometry from feedback filtering: decay and HF
controls change feedback coefficients, density/shape change network geometry,
quality changes network count, and diffusion changes serial gains. Early
pattern/size affect weighted taps and early input delay, while pre-delay changes
the late input delay. Tone enable, gain and frequency select or change expanded
matrices; sample rate affects several families together. These are observed
conditional dependencies under supplied values. An unchanged field in one
example does not prove global independence; disabled paths and selected curves
can ignore controls. All examples use owned buffers and original cleanup,
without engine initialization or game mutation.

One supplied historical bank parameter example matches all known stored live
settings as well as the derived configuration. This narrows the value candidate
but does not identify the loaded authored effect or physical bank occurrence.
Clones and identical authored settings remain possible. Reuse this configuration
capture; the next offline work belongs to parameter clone/update/lifecycle and
Event-source/provider ownership. Complete live histories, whole live buffers,
allocation generations, isolated Event contribution and hardware audibility
remain separate.

The separate
[`wwise_room_parameters_native.json`](../../scripts/game_data/contracts/wwise_room_parameters_native.json)
and `wwise_room_parameters_native` validator now authenticate the sparse signed
update-ID dispatch, clone copy spans, default/bulk initialization slots and
allocator termination. A clone receives distinct parameter storage, copies the
stored representation and sets both refresh and rebuild flags. It does not
retain an authored bank ID inside that copied parameter representation. Thus
identical live settings are compatible with several independently allocated
clones; matching values cannot supply origin or allocation generation.

The update dispatch distinguishes coefficient-refresh writes, topology/tone
rebuild writes and flag-free internal tuning writes. The named controls retain
their bulk-reader meanings; the internal tuning controls have exact numeric
update IDs and stored destinations, while their DSP roles remain unresolved.
Null value pointers are rejected before dispatch. Unsupported signed IDs can
return success without any mutation. The size argument does not bound the
original input read: bounded callers must provide the actual byte width even
when a recorded size is smaller. Owned original cases prove each defined ID's
value/dirty footprint and the no-op, null and size behavior without engine
initialization. The reusable `wwise_room_parameters_host` keeps all factory,
clone, value and termination storage owned and bounded; failures withhold output
and close allocator callbacks.

The same contract now owns complete generic template/registry/clone-carrier
consumers. A runtime registry matches the full plug-in class ID and selects its
parameter factory. Successful parameter initialization can replace the template's
retained parameter object, releasing an older one. The clone carrier retains
both the cloned parameter pointer and its source template, joins that template's
subscriber list and retains a reference. Subscription is a separately gated
branch. Parameter-class identity, template identity and processing-instance
identity are therefore three different joins.

Success alone does not establish readiness. The registry can return success
with no parameter factory and a null output. The template setter can also return
success after a failed class lookup, storing the requested class word while
leaving a null or previously retained parameter pointer. With a null template
parameter, the instantiation helper can return a value already stored in the
carrier. Require current class/pointer, normal return and the actual ownership
writes; do not turn any of these success returns into a fresh-clone claim.
Even failed clone allocation can link the carrier and retain the template
reference while storing a null parameter pointer. Readiness and retained
ownership are distinct outcomes, so failure is not evidence of no side effects.
The original empty-subscription release path frees a successful clone, removes
head or interior carrier links, clears retained pointers and releases references.
Owned cases cover both a successful carrier and a failed-clone carrier. The
earlier composition retains one template reference. Separate original lifecycle
cases now cover the last-reference branch and nonempty game-sync membership
under supplied private services; live engine subscriptions remain a different
claim.

An isolated original composition supplies a private registry row, bounded
allocator interfaces and an owned lock, with subscription disabled. Original
template initialization, cloning and carrier publication lead into actual
Room effect initialization with that clone pointer retained by the effect. The
result reproduces the accepted live network/filter configuration. Private
service inputs are restored and original carrier release removes both list
positions and restores the retained template reference. All parameter/effect
allocations are released; no engine initialization or game process is involved.
The generated
[parameter examples](../../reports/audio/room_parameter_lifecycle_examples_current.json)
and [template composition](../../reports/audio/room_parameter_template_composition_current.json)
record the supplied conditions. This does not execute the real bank load order,
subscription scheduling or last-reference template destruction. Carrier release
is conditional on empty subscription lists; remaining owned carrier headers are
discarded after those completed native release calls.

The reviewed
[`wwise_effect_lifecycle_native.json`](../../scripts/game_data/contracts/wwise_effect_lifecycle_native.json)
and `wwise_effect_lifecycle_native` validator extend the parameter owner without
duplicating its native groups. The bank's effect reader looks up a typed registry
object by object ID. A reused object receives another reference and is appended
to the current bank usage slot's object-pointer array when capacity permits.
Only a newly created object takes the template-loading branch. Several banks can
therefore retain the same live template; the later bank's matching definition
does not prove it initialized that template. A successful bank read can also
leave the array unchanged when its append capacity is unavailable. Require the
observed append and actual object pointer instead of inferring ownership from
the bank read's success or matching parameter bytes.

Bank usage-slot release walks the retained object pointers, decrements each
reference and invokes virtual final release on the last reference. Shared effect
final release selects its typed registry lane. A reference that is still held
prevents destruction. At zero references the selected routine removes the
matching head or interior registry entry, leaves the registry lock, invokes
virtual destruction and releases the object storage. Template destruction
terminates retained parameters, releases its owned arrays and state storage,
and destroys its critical section. The destruction guard is a thread/lock
condition, not evidence of deferred destruction. Owned original cases execute
the actual bank-array decrement, real template vtable, registry removal,
parameter termination and free route for both list positions, while separately
proving that a retained reference leaves the object alive. Private service
inputs and counters are restored, and all owned allocations are released.

Subscription has distinct game-sync and state/property routes. Game-sync setup
stores packed handles and registers the actual nested subscriber interface in
an entry/key-selected target array. Repeated handles/targets are deduplicated;
nonempty unsubscribe performs the typed lookup and removes the actual matching
target. Isolated original cases use the real carrier key getter, preallocated
owned lists and a supplied private registry to execute insertion, deduplication
and removal. These prove original native branches without initializing the
engine; they do not prove a subscription existed in the game. State registration
has separate entry creation and owner-handle writes. Its registration helper can
return true with no selected owner, so neither the outer Subscribe result nor
that helper's true result is a nonempty-registration witness.

The carrier's original nested game-sync interface has a proved callback slot.
Its thunk adjusts to the carrier's property aggregate, passes the packed
game-sync identity and observed value inputs through the selected aggregate
consumer, and can reach the retained clone's virtual parameter setter. The
setter transport feeds the recovered refresh/rebuild fields. Definitions can
produce no matching property or no update, so a callback alone is not a
parameter-write witness. The lifecycle reader requires a closed descendant
setter with a selected class, defined ID, non-null input, successful result and
matching permitted write footprint. Missing, rejected and unsupported setters
remain separate. The private original example invokes the real callback with
owned empty property definitions and preserves its no-write outcome. Origins
are confined to one continuous observation window; reopening a window cannot
reuse a generation whose intervening lifetime was not observed.

The dedicated `effect_lifecycle_observer_profile` and `effect_lifecycle_capture`
observe bank appends and source prefixes, template construction/loading,
parameter cloning/updating, actual target membership, state entry/handle writes,
effect initialization/Execute and release/destruction. This is an unsampled
lifecycle window; accepted DSP captures remain reusable. The initial window
opens automatically after provider initialization and can be toggled with the
existing controls. It does not promise that hooks preceded every startup bank.
Missing births, closed-window crossings, null-success paths, absent appends and
unobserved generations stay unresolved. Final-release return programs deliberately
avoid dereferencing destroyed storage. Parameter, template, carrier and effect
origins must be observed as separate identities; equal pointers or settings
cannot retrospectively supply a missing construction.

Shared and custom effect templates are derived objects. Their factories call
the common base constructor, then replace both the primary and nested state
address points. The base constructor's vtable is therefore a construction
stage, not the final live type. The reviewed derived address points retain the
common loader and indexable destruction route, but select their own deleting
destructors and typed final-release lanes. The lifecycle observer admits the
reviewed alternatives instead of filtering final release to the transient base
vtable. Original owned cases execute both factories, complete template loading,
retained parameter creation, clone/subscriber membership, Room processing and
bank-array last-reference destruction through those actual derived vtables.

The loader's source header, selected class, nested registry/factory output and
retained parameter must agree in one closed invocation. That gives an observed
loaded-parameter origin, which a later clone can carry into effect initialization
and Execute. A bank append can retain that loaded origin, including reuse by
another bank; reuse does not make the later bank the definition's initializer.
Matching bytes without the factory/load connection cannot supply the origin.
The source prefix and live bank-slot key still do not identify a unique physical
package occurrence.

Initial subscription application is separate from a later notification. After
registration, Subscribe walks enabled template property records, combines their
provided values with current aggregates and invokes the retained clone's setter.
The outer application ignores the setter status. An initial setter call therefore
proves neither actual target membership nor an asynchronous callback. The reviewed
complete body and operand bindings establish this distinction; the lossy saved
recording supplies diagnostic examples, not accepted live lifetimes.

The first lifecycle recording overflowed its transport queue. Its saved rows are
withheld from all live ownership joins. Offline diagnosis exposed engine-wide
bank-reader and unrelated effect-callback traffic, a missing full setter payload,
and the derived-vtable omission. The revised recipe observes bank bytes only
under observed effect-bank parents, selects real common effect-carrier interfaces
for subscription/retention, and selects detailed Room callbacks by their actual
retained parameter class. Target-registration descendants preserve real
subscriptions for other effect classes too; their retained parameter pointers
do not acquire an inferred allocation generation. Calls inside that scope remain
unsampled; exclusions and unreadable selection operands have separate counters.
Unreadable selection, loss, incomplete pairs or recipe drift withhold joins.
Execute retains ownership operands without repeating previously proved parameter
blocks every frame. Setter admission now compares the actual input payload and
dirty writes exactly; nonlinear level conversion requires an explicit identical
private original DLL comparison. Known lossy streams are checked in full without
building a semantic lifetime graph or admitting partial chains.

Selection must also follow failed read dependencies. If an inaccessible pointer
guards out a later class predicate, that predicate is unknown rather than a
proved exclusion. The recorder propagates this condition into its unreadable
scope counter, which prevents complete-coverage admission. Concurrent queue
producers assign record sequence numbers from reserved queue positions;
completion order after reservation cannot supply dequeue order.

Registry creation alone does not identify the allocation routine reached by
its indirect call. Loaded Room origins require the observed original parameter
factory nested inside the matching registry invocation, its returned address
point, and the same retained parameter at loader return. Target membership
during instantiation waits for that exact parent and parameter before acquiring
a carrier origin. Replacing a Room carrier with another effect class cannot
inherit the prior Room generation. Direct template destructor entry retires its
origin even without a final-release parent; a later reused address survives the
old invocation's return. Callbacks also require the retained parameter generation
to remain live and identical across entry and return, even when the carrier
itself has not changed. State handle appends require the selected owner to
remain identical across entry and return. Bounded original shared/custom cases
exercise the factory-to-load, clone-to-membership, processing and destruction
path without engine initialization; they establish conditional native behavior,
while complete live ownership still requires independent runtime evidence.

Nonempty original FX control examples now start at serialized template loading.
The loader creates RTPC definitions; Subscribe copies their keys and descriptor
pointers into the carrier's own list and registers its actual subscriber
interface. The descriptor remains shared with the template, while the carrier's
template reference protects that retained definition. FX curve parameter IDs
reach the selected plug-in's virtual setter; node property labels cannot name
them. Initial Subscribe application and later notification remain distinct even
when both write the same parameter.

Notification selection includes both the game-sync ID and its packed type.
The original curve evaluator supplies mapped old/new values, with a two-value
cache avoiding reevaluation. Composition can replace, apply an incremental
mapped-value difference, multiply retained contributions, or take their maximum
with a zero floor. Contribution replacement matches its parameter, source kind
and curve ID rather than repeatedly appending the same source. The reviewed
contract owns the mode declarations and borrows the existing curve-evaluation
catalog instead of duplicating it. Owned cached and uncached linear/no-scaling
cases establish these selected branches; other curve/scaling paths retain their
separate proof boundaries.

The serialized-control cohort also keeps an already initialized Room effect and
its impulse history alive across notification. The next original Execute
refreshes processing from the modified dirty parameter block without effect
reinitialization. Its output changes from an independently primed unchanged
control and matches an unhooked original with the identical notified parameter,
through a bounded multi-frame tail. Original unsubscribe, full subscriber
destruction and bank-array final template destruction leave no owned allocation.
Carrier release alone clears the definition count; full subscriber destruction
also frees that list's storage. These are conditional original executions on
provided serialized definitions and private services, not observations of a
shipped bank binding, engine scheduling, mixer/device output or audibility.

The maintained FX control reader and corpus gate inventory stored definitions
from authenticated available packages under the explicit selected native triplet.
The complete API frames parameter/media/RTPC/state/default data through exact
EOF; the prefix API retains its narrower boundary. The state loader has one
reviewed owner and borrows the existing FX loader and factories. Both derived
templates select the same state-reading virtual slot. State values store all
parameter IDs before all float values. Parameter IDs stay in the plug-in setter
domain; their native low-word retention remains separate from the stored integer.
Defaults replace an existing matching retained ID or append a new property;
initial subscriber application consumes the retained flag and value. Framing
does not establish allocation admission, effective states or accepted setters.

Room definitions include both empty and nonempty RTPC prefixes, so their class
alone cannot decide whether a notification should occur. The reviewed available
corpus distinguishes Room controls from Gain state definitions; an absent stored
Room state group cannot exclude runtime-added state bindings. Counts and source
joins remain generated reports rather than a duplicated build-specific catalog.

A selected shipped Room object also executes its original nonlinear scaling,
incremental level composition and plug-in level conversion on owned storage.
The exact physical object bytes feed original loading, definition copying,
automatic nonempty target insertion and existing-effect refresh. The unchanged
history reference remains byte-exact after applying the same original setters.
This closes conditional file-bytes-to-controls-to-Room-output behavior, without
claiming that the running game selected that package occurrence. Source-prefix
limits must cover the selected complete control definition before admitting
its framing; the earlier shorter prefix could establish parameter initialization
but could not retain every following curve.

The [built-in parameter contract](../../scripts/game_data/contracts/wwise_builtin_parameters_native.json)
and its validator close a separate static producer route. The component builds
retained ray rows, writes a calculated distance into each row, selects a row from
that same array and passes its exact pointer to the enabled built-in updater.
The first binding list carries packed control ID/type keys into exact namespace
lookup and scoped value application. A retained override can suppress that
application. Distance uses converted coordinate differences, an optional
retained probe and listener/source scaling; it need not equal raw world distance.
Authenticated Init settings connect the selected Room curve key to this stored
binding. Its authored default is separate from a computed live value. Actual
emitter/listener/probe objects, selected scope and complete callback lifetimes
still require runtime evidence; approximate SDK symbol matches do not establish
these joins.

The registered-notification original cohort calls the real list dispatcher on
the target array populated by original subscription. Its virtual callback reaches
the retained Room subscriber, with the caller return inside the authenticated
dispatcher. The shipped nonlinear definition then writes the retained clone and
refreshes the existing Room history, preserving equality with an independently
updated unhooked original. This extends the earlier direct-callback cohort;
input values and private services remain supplied. Initial applied values already
compose authored defaults with current aggregates, so serialized default floats
cannot be compared directly with those setter inputs. Scope creation can move
matching subscribers from the default target list into scoped lists. Immediate
changed values and retained transition processing are distinct paths; list
mutation/counters also govern dispatch. Neither the owned dispatcher example nor
an observed insertion proves continuous list membership, scoped migration,
smoothing schedules or actual emitter/listener ownership. A separate owned
scope-migration cohort executes the original key filter and list transfer on
that real registered subscriber. A mismatching key leaves the source list
unchanged; a matching key transfers its actual interface pointer into supplied
scoped-list storage. Original notification there reaches the same retained
clone and preserves the PCM comparison. Migration back permits original
unsubscribe, after which another dispatch produces no callback or setter;
final template cleanup releases all owned allocation. The supplied destination
is not a game-created scoped entry, so native scope-tree creation and lifetime
remain separate from this transfer proof.

The parameter-node original cohort also constructs the real entry and uses its
native scoped value storage/application before notification. Original target
association, callback dispatch and immediate updates reach the retained Room
clone. The same subscriber is removed from a different scoped header than its
initial insertion header, confirming original target association beyond the
earlier supplied-list transfer. Unsubscribe suppresses another update's callback, and parameter/template
destruction leaves no owned allocation. Its wildcard scope, zero transition
policy and private services are conditions. Per-object scope trees, nonzero
transition scheduling and live emitter/listener identities remain unobserved.
This route also calls the shared handle-registration helper. Its historical
State label is not a namespace proof: the reader reports an actual scope-handle
append with full packed key, low-word ID and raw type, and keeps anonymous
registration creation untyped. Boolean success without an observed owner/append
remains unresolved; neither row alone supplies named State subscription evidence.

The original ray cohort extends that node path upstream. Supplied finite
coordinates feed the complete original distance calculation; original special
binding admission and the enabled built-in updater carry its stored ray value
through the packed-key list into the real parameter entry, subscriber callback
and retained Room clone. Consecutive computed inputs supply consecutive old/new
callback values, and the existing-history PCM still equals an independently
updated original. Coordinates, owner/scaling storage, wildcard scope and immediate
transition policy remain supplied. The physical Init binding byte is joined
independently; its nonzero transition policy and authored default are not replaced
by the private cohort's zero policy/default in live conclusions.

The original transition prefix distinguishes rate-based and fixed-duration
policies. The rate path divides the current/target difference by its
direction-selected coefficient; the fixed-duration path selects that direction's
time value. It scales and truncates the result, then takes the signed maximum
with the requested duration. A nonpositive selected duration skips transition
manager allocation/update. Thus equal stored coefficients do not imply a fixed short response:
rate-based duration also depends on the magnitude of the parameter change.
Bounded unmodified-instruction replay proves this prefix separately from manager
allocation, tick scheduling, the full transition curve and live policy selection.
The initialization prefix converts that duration through native frequency and
the context's frame quantum into a truncated quantum count, retaining a start
tick. It reads the same quantum owned by the codec/context contract. A separate
unmodified prefix replay checks this conversion under provided frequency/quantum;
the file's initialized globals are not observations of a running device, and
manager advancement/completion remains outside this prefix proof.
Complete original manager/advance/receiver bodies close the separate static
completion route: visit both retained lists, compute progress or select the final
target, snapshot users before virtual notification, and carry value/completion
into the parameter receiver. Completion clears its retained transition; delivered
floats re-enter scoped value application and the existing subscriber path. This
is a static route rather than an executed full smoothing schedule; manager
creation, active clock globals and all curve/filter selections remain conditions.

The remaining origin question requires a live loaded template and physical bank
occurrence, its parameter allocation, each clone carrier and the parameter passed
into effect initialization, with replacement/release intervals. Authored Sound
effect slots distinguish an enabled reference from a bypassed reference even
when both select the same shared template and external-source cookie. Their
typed Event/Action/parent references are stored route candidates, not observations
of effective bypass, selected external files or admitted voice processing. Existing late
Room snapshots cannot retrospectively observe template loading. Continue
reviewing the lifecycle recorder, read programs and reader before requesting
its live run; an unchanged configuration recording cannot close it. Event/source file selection
and full live DSP history remain independent gaps.

Hook creation is a separate preparation requirement from forwarding ABI and
operand replay. The initial contribution run stopped before readiness and
recorded no native observations: the hook backend rejected the ramp entry
because it decoded an unsupported vector instruction after its complete jump
prefix. That following instruction is not relocated. The corrected backend
decodes only displaced instructions and still rejects unsupported instructions
inside that prefix. Private original-DLL examples now exercise creation of
every static native recipe entry and enabled forwarding of both accumulation
trampolines, with complete-buffer equality. Startup errors retain the failing
hook name, RVA and backend status. These local checks do not replace a closed
live observation window.

The first handoff attempt recorded no observation window or native rows. The
provider ran and excluded outside-window calls, but readiness and zero queue
loss do not establish that recording started. The user pressed the audio hotkey
without a visible overlay. Code review found that the overlay expired during
the host's longer prelaunch wait; the session's attachment followed that short
expiry. The overlay now follows the launcher's lifetime, and the host offers
an `audio` console command using the existing event control, so manual start
does not depend on the overlay. The importer reports a missing or unclosed
window as `noObservationWindow`, leaves native data uninterpreted and emits
bounded diagnostics. Empty handoff sessions cannot be marked complete by the
runtime. A repeat still needs a closed, loss-free window and all required
endpoints before admitting the buffer/device join.

Dense unsampled source observations are checked and counted in full; retained
examples are bounded per exact current identity tuple. Publication/reset example
arrays are likewise bounded independently of the live interval state and counts.
Do not count these examples as the full source stream. Provider selection counters
span the provider lifetime, while saved observations are filtered by recorded
invocation into closed windows. The native worker discards outside-window records
during final quiescent draining. Selection totals must bound reviewed entries;
their excess remains explicitly unattributed and does not prove window completeness.
Zero intentional skips and zero queue losses remain required for conditional
source/reset intervals; scoped counters do not certify a whole engine frame.
Native publication precedes the associated frame-reference release. The reviewer
therefore distinguishes a current source-write/release interval from a published
first-row projection. The latter requires matching route/bus/row/descriptor and
sample fields, carries any observed release explicitly, and is invalidated by a
new source write, replacement publication or bus reset. It does not certify the
allocation's continued validity. Intervening writes/resets during mixing also
withhold the corresponding completed interval join.

The completed conversions also retain a direct numerical witness: captured
first-planar-channel input multiplied by the captured constant gain, rounded to
float32, exactly reproduces the saved interleaved first-channel prefix. Audio's
`sink_pcm_witness` domain checks this limited equation, rejects unsupported
ramps/layouts/nonfinite inputs, and keeps silence distinct from content identity.
The second input channel and whole buffers are not captured by this comparison,
and equivalent sample values do not identify a particular native branch. Another
finite nonzero live voice prefix exactly matches original native decoding from
its matching physical WEM. That isolated run covers a bounded decoded extent
under the retained allocation/setup-lock conditions, not whole-stream parity.
The expanded receipt tree also exposes drift in the supplied package census's
VFS audit/cache inputs. Preserve their historical digests and withhold current
whole-corpus/overlay completeness. Fresh positive typed-header and selected-entry
comparisons retain their limited scopes, and selected native gates still pass;
those local checks do not refresh the complete census.

The initial Action capture mislabeled two reads: the actual serial and retained
allocation follow different checked operands in the source-queue owner. The
corrected playback declaration uses those operands and retains the old storage
only under anonymous names. Do not reinterpret historical fields by label or
join their values as playing IDs. Pre-binding context object reads likewise
require an existing embedded owner. Non-evicting receiver buckets, a per-hook
sampling budget and narrowly retained getter children now replace the capture's
collision-prone, broadly nested frame sampling. The corrected session confirms
loss-free transport for its sampled workload; this is not a guarantee for every
future workload.
Do not use recursive refresh, a zero-default manager, stored bus ancestry or
the supplied null-component branch as effective game loudness.

Vorbis has two distinct comparison gaps. Emulator output differs from isolated
host output; normal initialized-data and supported CPU-subset probes do not
close that gap. Original host output also differs from the external decoder
reference, but by a much smaller amount. Whole native preparation returns
exactly the same float bytes as separate direct host codec initialization for
the shared file, narrowing the preparation-state question. The saved WAVs are
original host codec output, with reference differences explicitly recorded;
do not label equality successful or infer a game defect. Native Vorbis parity,
live registry/provider buffer identity and lifetime, inherited authored routing,
remaining processing branches, real device execution and audibility still need distinct
proofs. The conditional owner/frame/mixer/submission cohort above is not blocked
on decoder-reference equality and does not close those independent gaps.

An opt-in `--include-source-bridge` recipe uses that companion to capture the
selector, clone, wide-text setter, owner factory and constructor alongside the
consumer. It retains the playback blob's fixed roles and samples only the first
descriptor; descriptor closure requires an allocation containing only that
descriptor. The setter
arguments cover only the declared register inputs; additional stack inputs do
not become a complete signature claim. The strict auditor requires the exact
generated recipe and selected inputs. This observation can connect synchronous
selection and owner transport, but it does not observe queue allocation creation,
generation or lifetime. Managed request-to-source ownership across the queue,
backing-file identity, codec choice, decode success and audibility stay open.
Saved classic and consumer recordings contain none of the newly added selection
hooks, so static admission does not add those observations retroactively.

Audited source-bridge recordings now directly observe descriptor text selecting
a cloned native source and that source passing through a factory, constructor,
embedded consumer and nested LockDataPtr. The observed config address point
dispatches directly to the existing reviewed factory; it is authenticated
separately from the earlier conditional wrapper address point. The constructor
retains the same selected source, and its returned owner is the consumer's
adjusted owner. LockDataPtr copies the retained path-storage pointer with a zero
byte count. This is synchronous native text and pointer transport, with no
backing-file, media-byte, codec, decoder or audible-output inference.

The reusable
[`audio_source_bridge_relations.py`](../../scripts/webui/story_recovery/audio_source_bridge_relations.py)
derives its roles, fields, callsites and dispatch choices from the authenticated
companion projection and exact profile. It checks actual immediate parents,
same-thread nesting through return, caller addresses, descriptor and setter text,
clone results, constructed-owner identity, stored-source fields and consumer/Lock
snapshots. Each chain stays inside its own selector interval; repeated pointer,
cookie or path values never join separate selectors or managed requests. Unknown
dispatch choices, omitted calls and branches outside the single-descriptor scope
remain unresolved. Malformed applicable evidence withholds source summaries,
including errors after the displayed sample caps. All candidates are checked;
the report retains a bounded path inventory and representative samples per path.

Generic sampling keeps UTF-16 pointer-field reads distinct from direct-address
text reads. A terminated read stops at NUL within the declared budget of 4096
UTF-16 units, and declared guards run before pointer dereferences. Inactive
branches, descriptor allocations outside the single-row scope and null paths
emit explicit null fields; constructor owner members are sampled only after
return. The strict auditor accepts declared inactive nulls, but failed applicable
reads or malformed pointer returns withhold source summaries.

[`prepare_audio_source_observer.py`](../../scripts/webui/story_recovery/prepare_audio_source_observer.py)
reconstructs the classic minimal profile for validating saved paired observations. It requires
all four source hooks plus both managed bridges, captures fixed source/info/
output fields at entry and return, retains source and output pointer identities,
and records call-pair, nesting and return-address evidence. It reads no media
bytes and follows no pointer chains. Native hashes, exact exception-directory
extents, instruction witnesses and managed identity/signature/windows gate
profile publication; malformed or missing/mismatched inputs withhold it.
Required-hook declarations remain part of each frozen profile; older profiles
retain their original optional-hook boundary.

The observer checks the reported module name, path and mapped PE image extent
against the selected disk files and retains its validated ASLR base. Disk length
and mapped image size are distinct. These facts authenticate file identity and
reported extent; they do not attest the contents of mapped code pages. Return
addresses become module-relative only inside those authenticated extents;
addresses outside them remain unresolved callsite observations.

[`audit_audio_source_capture.py`](../../scripts/webui/story_recovery/audit_audio_source_capture.py)
is the post-capture gate, run after the capture process exits. It freezes bounded
event and adjacent diagnostic streams, records the digests of exactly those
bytes, and rechecks selected file identity. Source claims require contiguous host
and agent sequences, clean event/diagnostic delivery receipts, closed sessions,
zero active managed/native frames, unique session-scoped native capture IDs,
matching hook/thread/parent/return-address identity, and complete fixed-field
samples at both entry and return. Reused IDs in different sessions are distinct;
non-source rows do not create source claims. Missing pairs, failed samples or
late errors withhold all source-pair claims while preserving the raw streams.
Intentional cleanup detach is recorded separately from an unexpected detach.

The complete live minimal-profile recording now passes the selected-build,
fixed-field, pair, sequence and clean-stop audit. It observes SetSource info
and scalar overloads plus LockDataPtr; the memory overload was not observed.
Managed external requests retain distinct Chinese character-voice paths with
one shared cookie, but native calls have no synchronous managed-parent chain.
The direct-pointer LockDataPtr observations have no previously recorded
SetSource at their source addresses. Other same-address source-state matches
cross threads, so they remain conditional on uncaptured copies, resets and
lifetime. No source-to-voice-file or codec join follows from cookie equality,
pointer proximity or timestamp order.

The reusable auditor retains immutable full-input digests and reports the
explicit byte/event budgets for larger recordings; raising a budget does not
truncate or relax sample, sequence or clean-stop checks. Generated per-session
inventories stay in reports. Declared source consumers have a separate bounded
sample budget, so startup source calls cannot hide a later consumer pair.
Samples retain native parent capture IDs, but a retained ID is not a verified
nesting edge. The separate `sourceConsumerRelations` audit checks the recorded
immediate active parent, same thread, ordered entry/return intervals, and the
owner/source/output roles derived from the authenticated profile. It compares
the complete entry/return field snapshots before admitting a synchronous
consumer-to-LockDataPtr relation. Invalid recorded relations withhold all
source summaries; absent or undeclared parents remain explicitly unresolved.
Neither a verified synchronous edge nor a same-address state match bridges a
managed voice request across the asynchronous queue or establishes pointer
lifetime. Saved consumer recordings now exercise both source flag states and
the requested managed character path, but their native calls have no captured
managed-parent chain. These saved paired observations remain separate from
native entry-only evidence.
File identity, codec choice, decoded content and audibility remain open.

The separate
[`wwise_owner_carrier_native.py`](../../scripts/game_data/wwise_owner_carrier_native.py)
owner authenticates the reviewed primary-owner command queue and carrier-control
transport through its
[`contract`](../../scripts/game_data/contracts/wwise_owner_carrier_native.json).
It reuses the admitted source constructor on the same opened selected images.
The constructor installs a primary address point whose command method queues
that owner. The complete enqueue body stores the owner in a queue payload and
returns a success or allocation-failure status; it does not retain or release
the owner. The drain groups nodes by a stored batching word, selects a carrier
through current or pending decoder-owner comparisons or the owner-stored carrier,
then dispatches the selected control command with that same payload owner.
Nodes are recycled or freed. Neither the batching word nor a reused node address
establishes a unique object generation or a retained asynchronous lifetime.

The selected carrier-control entry provides a narrower direct observation point:
its carrier and primary-owner arguments are compared against current or pending
decoder ownership before cleanup and state changes. This is a control and
cleanup boundary, not proof of decoder creation or codec selection. Its optional
observer declaration projects only entry-time fields, because the handler can
release a decoder before returning. It includes guarded nullable decoder pointers,
their owner fields, and the primary owner's already admitted stored source fields.
The opt-in owner/carrier recipe captures this entry alongside the source-bridge
hooks.
A matching entry snapshot establishes local carrier/decoder-owner pointer
equality only; the samples are not atomic and do not prove which later internal
branch executed. The pure
[`audio_owner_carrier_relations.py`](../../scripts/webui/story_recovery/audio_owner_carrier_relations.py)
checks the selected caller and primary address point, typed nullable fields and
every candidate before applying its display cap. Malformed applicable evidence
withholds the source summaries. A snapshot
does not inherit the generation or path ownership of an earlier selector
recording. The source direct-pointer flag is not a unique text predicate, so this
declaration does not reinterpret an arbitrary source data pointer as UTF16.
Provider initialization, decoder generation, media content and audibility remain
separate missing observations.

The offline provider-preparation route is independently authenticated by
[`wwise_decoder_provider_native.py`](../../scripts/game_data/wwise_decoder_provider_native.py)
and its reviewed
[`contract`](../../scripts/game_data/contracts/wwise_decoder_provider_native.json).
The gate checks complete preparation and caller unwind groups, field encodings,
branch targets and the common singleton slot against the explicit selected
managed pair and Wwise image. Its owner/source fields must agree with the
source and owner/carrier contracts on those same opened images. This route
does not depend on a new capture or inherit observations from an older profile.
Agreement between these field layouts does not identify a carrier's live
decoder as the preparation helper's input, or prove a shared allocation generation.

The preparation helper reads the decoder's primary owner, then its stored
source. Outside the alternate source-kind branch, the pointer-selection flag
chooses either the stored data pointer or stored numeric word for a temporary
provider descriptor. The direct-data flag supplies a separate Boolean; it is
not a unique text predicate. The upper halfword of the source argument is
copied into a flags descriptor without proving its codec meaning. The
alternate source-kind branch instead passes an owner-held pointer and word
through a different virtual slot. Both calls receive the address of the
decoder's provider output field. These are direct reads and conditional static
transports, not proof of an indirect slot implementation, concrete provider
instance, file opening or live selector-to-provider continuity. In particular,
do not apply the helper's branch rules to a saved source snapshot and call it
an observed provider invocation: that helper was not hooked in those sessions.

An additional reviewed
[`source-provider dispatch contract`](../../scripts/game_data/contracts/wwise_source_provider_dispatch_native.json)
and [`validator`](../../scripts/game_data/wwise_source_provider_dispatch_native.py)
authenticate the complete source-based preparation and storage-wrapper groups.
The source-based routine reads its source through the request argument rather
than through a decoder's owner. It constructs the conditional pointer-or-word
descriptor, calls the initialized ordinary or alternate factory slot, and
passes an output context not sampled by the entry recipe. Authenticated return
sites distinguish this caller from decoder preparation. The optional dispatch
gate reuses the opened selected images and fails independently: local entry
admission survives, but caller roles and address-point comparisons are withheld.
Captured ordinary-provider and alternate-factory address points match their
reviewed tables locally; input text does not prove a retained descriptor,
factory result, completed copy, file dispatch or PCM output.

The reviewed
[`external-package contract`](../../scripts/game_data/contracts/wwise_external_package_native.json)
and [`reader`](../../scripts/game_data/wwise_external_package_native.py)
close a separate conditional naming route. The external helper converts valid
terminated UTF-16 to UTF-8, folds only ASCII capitals, and computes
multiply-before-XOR FNV-1-64 over the complete path. It preserves the extension
and separators. The external-key consumer compares a full-width key in its
typed package table and separately compares language. Do not reuse the sibling
ordinary helper, which strips the extension and uses a narrower key, or apply
Unicode lowercasing/slash normalization to captured paths. Candidate keys from
saved provider inputs resolve to decoded voice candidates; a calculation alone
does not observe an invocation or returned row. The admitted source-I/O
recording separately observes the hash-input paths and lookup-input keys with
the required external kind at authenticated package-consumer return sites.
It attempts each key against multiple package tables. The contract also
authenticates default I/O initialization and table slots: the selected I/O
batch slot adjusts to the primary context and dispatches descriptor requests
to the package lookup slot. A captured matching I/O address point admits this
local implementation identity, without proving any returned package row.
The separately reviewed
[`retention contract`](../../scripts/game_data/contracts/wwise_provider_retention_native.json)
and [`validator`](../../scripts/game_data/wwise_provider_retention_native.py)
authenticate primary-provider descriptor/device reads and the device's retained
I/O argument for the expanded recipe. These fields remain local, guarded entry
snapshots, without atomicity, pointer generation or successful I/O claims.

The reviewed
[`package-result contract`](../../scripts/game_data/contracts/wwise_package_result_native.json)
and [`validator`](../../scripts/game_data/wwise_package_result_native.py)
authenticate the completion dispatcher, primary completion slot and external
package descriptor writes. The dispatcher stores the request's result on the
provider and passes its retained request and status to the completion handler.
The package branch builds length, block geometry and an opaque package pointer
from a selected external row. The new entry recipe samples before the handler
can release the request, so no return-time dereference is needed. Local
provider/request/back-pointer and result equality can be checked under the
authenticated caller and address point; it supplies no cross-call lifetime.
A complete expanded recording now admits local status-success completions,
including terminated voice text and descriptor geometry. The provider retains
the same request and result pointers within each checked entry. Gated full-path
hashing matches the external descriptor key low word, and the sampled byte
offset agrees with the reviewed modulo-width block calculation. These are
local comparisons, not entry pairing. An installed external-source row also
matches the full calculated key and descriptor geometry; its extracted WEM
decodes to the same PCM as the existing voice FLAC. This closes an offline
selected-entry comparison, not the live backing-file join. The game decoder
instance and audibility stay separate even on status success. This optional
gate reuses the selected images with validated storage
and package dependencies; missing or mismatched inputs withhold its claims.

The reviewed
[`package-read contract`](../../scripts/game_data/contracts/wwise_package_read_native.json)
and [`validator`](../../scripts/game_data/wwise_package_read_native.py) authenticate
the default read slot, complete chained read and completion bodies, the
`ReadFileEx` import, callback transport and a complete bounded pre-transform
leaf. The true read entry includes the early nonpositive-count return before
its stack setup; an interior stack instruction is not a substitute entry.
The completion passes its transfer and cookie-held descriptor to the transform
leaf only on zero platform error, then dispatches the transfer callback. The
leaf reads a descriptor flag, key low word and byte offset plus transfer
position, buffer and transform length. The separate reviewed
[`package-transform contract`](../../scripts/game_data/contracts/wwise_package_transform_native.json)
and [`validator`](../../scripts/game_data/wwise_package_transform_native.py)
authenticate the complete transform body and its aligned DWORD/tail path.
The descriptor-relative, position-indexed key derivation and little-endian XOR agree with the
offline package reader for offsets divisible by a DWORD. This conditional
equivalence does not promote the misaligned leading branch for short lengths.
The complete body retains a useful static boundary: its nonzero alignment
selects the remaining bytes of the current DWORD key, and the leading loop
writes that span before comparing it with the requested length. The offline
reader clamps its own leading span to the supplied length. Therefore short
misaligned requests cannot inherit the aligned equivalence claim. For longer
requests the branch advances the seed and rejoins the checked word/tail path;
extending admission requires explicit leading-branch operand and control-flow
witnesses, not another sampled playback. The current native contract continues
to admit only the aligned domain.
The same contract authenticates the observed transfer callback's anonymous
receiver-slot dispatch; it does not identify that receiver as a codec.
The expanded transform contract also authenticates a complete unwindless
transfer-block initializer, its complete device/anonymous-receiver producer
callers and the conditional primary-provider completion slot. The initializer embeds the
transfer record, stores a block back-pointer as callback user data, clears its
I/O cookie and retains the block owner. The reviewed anonymous read queue supplies that
owner and stores a receiver on completion nodes. Callback dispatch recycles the
block and walks those nodes; the conditional primary-provider handler changes
anonymous request-state bits and wakes downstream work. This establishes a
static transport protocol, not a PCM decoder. The admitted recipe did not sample
callback user data, block owner or completion-node receiver. Those values must
not be reconstructed from matching transfer pointers or timestamp ordering.
The read-queue producer's concrete class is not inferred from shared field
offsets; only the receiver slot on the authenticated primary address point has
that conditional family identity.
The same contract now proves a separate constructor-installed queued-receiver
interface: its queue and completion slots join the reviewed queue producer to
its own state handler. This is conditional on retaining that address point.
The constructor's factory branch occupies a different manager slot from the
authenticated decoder preparation route; shared node layouts do not bridge
those families or identify a codec. Pending-list removal and storage release
in completion helpers are transport behavior, not decoded output.

The expanded recipe keeps prior versions exact and adds read-batch, platform
completion and pre-transform entries together. Bounded fields retain the first
batch record, error/transferred-byte arguments, descriptor geometry, local
cookie equality, the descriptor file-handle value and one guarded pre-transform
buffer DWORD. The handle is opaque here; no filename query or handle-lifetime
join is performed. A complete expanded recording now admits zero-error
platform completions with actual byte counts equal to local requested counts,
plus independently checked pre-transform descriptor/cookie entries. The selected
voice's transform ranges span its descriptor length. All sampled encoded DWORDs
in the admitted geometry cohorts match candidate rows in the bounded CN,
shared and audit package index. These comparisons use every admitted entry,
not the bounded display sample. The reusable
[`word matcher`](../../scripts/webui/audio/semantics/package_read_witness.py)
reads headers and sampled bytes only; it explicitly does not authenticate an
entire overlay corpus or whole package digest. The voice's first sampled word
predicts RIFF under the reviewed aligned XOR path, but that clear word is a
calculation, not a recorded post-transform sample. Transform-range unions are
metadata coverage, not retention of every buffer byte. Zero-error completion
is not full payload evidence or audibility, and separate entries do not prove
allocation generation. Missing
or mismatched read dependencies withhold that child on the same selected images.
The transform proof is an optional child: failure withholds predicted clear
words and callback identities while preserving independently admitted read
facts. Reuse this combined recording for further offline work; do not request
another replay merely to extend the observation recipe incrementally.
Once Audio has a current publication, the single builder's native-entry-only
mode can re-audit and atomically refresh this independent disclosure. It checks
the publication schema/language and refuses a concurrent index replacement;
failed native admission publishes an unavailable child with no stale rows.
The next combined transfer recipe preserves earlier recordings exactly and
adds self-contained transfer/block owner and completion-node receiver fields.
Its dedicated
[`receiver summary`](../../scripts/webui/audio/semantics/transfer_receiver_observations.py)
checks local back-pointers, reviewed interface address points and direct
receiver/node equality without pairing separate entries. The dispatcher
recycles its block before receiver invocation, so handler carrier-block fields
remain raw observations even if addresses match an earlier entry. The recipe
samples one list head and one buffer word, not a full list, payload or PCM.
Its new managed external-post ABI retains original external cookie and raw
Beyond codec arguments only after the full selected signature/backing gate.
This extends what a future single recording can answer; it does not add those
missing fields to existing recordings.

Receiver diagnostics must distinguish a null completion-node argument, a
readable zero carrier link, and an inaccessible field. The retained dispatcher
body clears the carrier's transfer-block link before calling the receiver, so
another handler-entry capture cannot recover the former block through that
link. The typed dispatcher witnesses still need a separate proof of the
clear/recycle sequence. Additional primary-handler callers and null-node paths
are static review targets; they do not become dispatcher-owned transfers from
address or timestamp proximity.

Preparing that recipe is not a reason to request another capture. Its open
receiver/ownership join is runtime evidence; no additional stored-file decoding
coverage follows from observing one more voice. Apply the corpus-first capture
admission policy in the game-data entry point before recording. Representatives
should target missing shared branches rather than named characters, and one
window should combine the justified contrasts. User actions are probes: the
admitted entry counters decide which paths were actually observed.

A useful transfer window must pass complete, closed, zero-loss admission and
contain both a locally checked default-I/O transfer and a reviewed receiver
handler entry with the exact dispatcher caller and receiver/node equality.
Observing both reviewed receiver families is a useful contrast, not a reason
to repeat the same voice until one appears. A manual voice, ordinary sound
effect and accessible streaming transition may probe those families in one
window. Stop after each available probe once and a brief idle; an absent
family requires reassessing its producer path before another request. These
local checks establish selected runtime structures, not a cross-entry pair or
an end-to-end managed-request-to-media binding.

Read summaries report encryption flags, relative offset alignment and origin,
and complete/partial/invalid descriptor-range cohorts over every admitted
entry. Display samples are selected across strata so a busy transform path
does not hide another hook or receiver family. These are observed-window
dimensions, not installed-corpus prevalence, allocation continuity or retained
payload coverage. An unobserved branch remains open even if another branch has
many samples.

The optional `--include-storage` gate authenticates the reviewed
[`provider-storage contract`](../../scripts/game_data/contracts/wwise_provider_storage_native.json)
through [`wwise_provider_storage_native.py`](../../scripts/game_data/wwise_provider_storage_native.py)
on those same opened images. Complete initializer, factory, constructor and
copy groups, bounded unwindless leaves, and selected table slots close the
conditional downstream dispatch: if the singleton retains the reviewed
initialized address point, its ordinary slot constructs a provider and returns
the secondary interface on the reviewed success-status branch. A non-null
UTF-16 descriptor text takes a length, allocation, bounded word-copy and
explicit NUL-termination route into owned storage. The alternate slot instead
constructs a different provider, retains the incoming pointer and anonymous
word, and returns the allocation base. The word's unit is not established.

This is conditional static construction and storage, not an observation that
the singleton remained unchanged or a saved voice used this decoder family.
Historical provider reports describe a different Wwise image; their addresses
and SDK labels do not admit current claims. File handles and reads, codec
identity, request continuity and allocation generation remain separate open
joins. Storage-gate failure withholds only these downstream claims; validated
preparation evidence remains available. No old capture recipe is extended.


## Capture retention and reuse

Keep the raw trace, adjacent diagnostics, exact session profile and preparation
report together. The reusable
[`archive_runtime_capture.py`](../../scripts/webui/story_recovery/archive_runtime_capture.py)
records a SHA256 inventory and verifies every ZIP member. This proves retained
byte identity, not successful hooks, clean closure, selected-build validity or
any playback claim; the strict capture auditor owns those gates. Archives and
per-session inventories remain local generated evidence under
`reports/audio/captures/`. Live launchers and instrumentation agents have been
removed; archive and audit commands operate only on saved files.
A responsive agent stops recording new calls, finishes previously captured pairs
and returns a drain receipt before the host attempts one unload. The strict
auditor requires that protocol and a successful drain when either new receipt
field is present; saved recordings without those fields retain their original
receipt checks.

A session interrupted by process exit may lack a final receipt even when
retained entry/result rows are paired. Archive checksums preserve those bytes,
but the strict auditor withholds source summaries and rebased relations. It
validates fixed fields independently and skips derived caller checks when
closure/module verification is absent, avoiding false null-RVA callsite errors.
A raw voice-path row can confirm the recorded path; missing carrier rows in an
interrupted session do not prove that a backend never executes. Preserve such
sessions as diagnostics, without replacing earlier validated publication or
synthesizing a clean-stop receipt. Process discovery and module readiness
alone do not supply an armed observation or a successful saved recording.

A drain receipt proves captured-pair completion and delivery, not interceptor
or thread quiescence. Unrecorded calls after the stop request are outside its
counters, and a stalled host RPC has no independent deadline. Offline receipt tests
do not establish live game-crash prevention. The reported stop-time crash
has matching Windows process evidence and a preserved dump showing an execute
access violation outside loaded module ranges. The dump lacks stack and code
bytes, memory protections and unloaded-module evidence, so it cannot identify
the former allocation or establish the crash cause. The reusable offline
[`audit_capture_crash_dump.py`](../../scripts/webui/story_recovery/audit_capture_crash_dump.py)
authenticates bounded dump framing and lists stored exception/context and module
range evidence; raw stack words are explicitly distinct from unwound frames.

The native Audio callback queue runs throughout the attached lifetime;
the writer filters retained rows to the manually selected windows. Its loss
receipt is cumulative. A correctly closed window, complete managed pairs and
contiguous retained entry capture IDs do not supply a missing interval-specific
loss receipt, especially at the first and last retained entries. Failed global
zero-loss admission therefore still withholds semantic publication. Such a
recording can guide static caller review and recorder diagnostics, without
replacing earlier admitted observations or prompting an automatic replay.
The recorder now retains a larger heap-backed burst buffer and drains more
frequently while Audio is observing, without increasing periodic status-write
frequency. Its versioned `recorderSnapshot` at window boundaries and finalization
records lifetime counters, observation time and the observed reservation
high-water mark. These concurrent diagnostic samples are not atomic counter
tuples and cannot be subtracted to prove a loss-free interval. Historical
recordings lacking them retain their original admission boundary.

Historical recordings remain useful for the observations their original hooks
captured. Retain their profiles, diagnostics, receipts and audit/import outputs
when available, and distinguish absent historical files from evidence created
later. Label any current revalidation copy of a historical profile as such;
it is not evidence that those exact bytes were retained at capture time. When
a raw log omits a manifest digest, matching module facts and a regenerated
profile cannot authenticate the full capture-time manifest or settings bytes;
the regenerated profile remains a revalidation artifact. A new client build or
profile cannot retroactively add a missing hook, field, parent chain or
source-lifetime sample to an old recording. Recheck the
saved inputs with the appropriate build and profile gates before reusing claims;
an archive verification alone never promotes a historical row to current.

Historical source profiles compare operational recipe identity separately from
the top-level `evidenceBoundary` prose. The same boundary keys and string value
types are required, while hooks, argument types, offsets, limits, source pins
and every other recipe field must still match exactly. Only descriptive wording
may differ. The fresh selected-build audit supplies the published claims; old
prose supplies none. The public Audio command's `--runtime-source-only` refresh
replays the original bundle and atomically replaces its source/owner child,
preserving independent observations and refusing missing or changed inputs.

Start with reusable saved sessions and static evidence. Request a new bounded
capture only for a named unresolved join or representative branch that existing
recordings cannot decide, and specify the preparation and playback action that
exercises it. Shared callsite and format behavior does not require the user to
record every character, line or voice. An unobserved branch stays open until a
representative capture or an independent proof covers it.

Name-based ModelView route re-derivation proves the current consumer and its
listed callsites, named field-store checks and endpoint callee inventories. It
does not inherit the earlier build's branch guards, endpoint argument/return
flow, adapter connection or async preparation status. The semantic projection
labels these routes `currentBuildCallsitesOnly`; stronger endpoint claims remain
`notReprovedOnSelectedBuild`. This distinction preserves authored behavior and
possible media without claiming a complete current native path. Re-derivation
requires the explicitly selected GameAssembly/metadata pair and never selects a
different default installation.

The positioned recipe in `audio_model_view_consumers.json` names only current
state/custom-state, model-context object, transform, position and positioned-play
interfaces. Its caller is re-proved from the selected native pair. These calls
occur on different guarded paths; their presence establishes no argument binding,
field write, endpoint chain, object/audio owner or playback execution. The removed
Entity audio-ID accessor is not a current obligation. The projection retains
`currentBuildCallsitesOnly` and leaves all stronger joins unproved.

AI-bark re-derivation requires a named callsite for every adjacent pair in the
displayed route, including the caller's owned fragments and bounded helpers.
A shared ancestor or matching iFix patch marker alone does not prove that pair.
The result records current callsites and a narrow call-graph boundary; it does
not inherit prior argument transport, branch selection or runtime ownership.

Enemy voice-type mapping re-derivation reads each integer key and string literal
from the same `Dictionary.Add` argument window in the named static constructor.
Literal load order is not a mapping proof. An unknown argument shape, additional
unresolved addition or different receiver withholds the route. These constructor
pairs and the consumer's reach to `ResponseOnEntity` do not prove the consumer's
dictionary selection, argument transport or live action execution.

## Eliminated readings

- The managed adapter's first scalar as an external cookie or package key; it is the Event ID.
- A posted Event ID as a unique external-file identifier (one Event ID may accompany several paths).
- Beyond `AudioCodec` values as `AKCODECID_*` constants.
- The sourceInfo word as the registration serial (separate global slot).
- The locally assembled integer (temporary state + build constant + context field) as the key.
- The manager descriptor field as a path/provider/codec input (ownership retention only).
- A join hit as media selection (lifecycle append only).
- The device's secondary address point as the pump's context producer (field serializer only).
- The provider callback as the codec stream's indirect callback (queue/state transition).
- The default-I/O interior branch as an independent function (hook the real entry).
- Catalog row names as roles: six SDK-named rows were all misnamed, none an external-source function.
- `CAkSrcMedia` as *the* voice path (made before the other two families were known).
- An activation manifest produced in this repository (the host owns the conversion).
- Silently trimming an authored PlaySound string.

## Recovery queue

1. Prioritize the Event identity through its registered Action list, queued
   descriptor allocation and selected source, then the actual backing bytes,
   codec and output. Static registry/target/cookie transport and selected
   offline package-to-PCM comparisons are checked. Authored registration/list
   creation, conditional codec construction and selected format metadata now
   have original-byte proofs. Selected Opus sample computation and its media
   wrapper consumer now execute offline and agree with independent host
   execution. Selected numeric Event sources also execute exact-key resident
   lookup, whole preparation and sample-wrapper output on the host CPU under
   explicit table/input/provider conditions, with original readable-row
   admission. Original node/source preparation also requests numeric file
   bytes, allocates/reads/publishes the resident buffer and preserves PCM through
   immediate or deferred preparation. Original package header/load/list routines,
   numeric lookup and aligned media transformation now preserve that PCM under
   supplied load-call and stream-interface conditions. Prioritize the game's
   load/reorder sequence and actual device/worker scheduling; original standard
   stream reads, OS completion/decryption, resident publication and memory
   provider now preserve PCM under supplied dispatch and owner conditions.
   Original parameter refresh, policy/frame admission, context construction,
   unity-rate frame conversion/release, filter bypass, master-bus output and sink
   submission now compose into one conditional stream-to-render-buffer cohort.
   Whole frame preparation now publishes descriptor fields and applies the
   initial counter correction under an empty route list, preserving exact PCM
   without the omitted-preparation cohort's leading silence.
   Original route attachment, nonempty preparation, context gain refresh,
   descriptor publication, bus admission/matrix mixing and frame reset now
   compose into that cohort without a helper-supplied source-to-bus descriptor.
   Sample values agree completely; signed-zero bit changes are recorded
   separately. Prioritize authored owner/effect parameters and bus selection,
   remaining route branches, varying pitch/rate/transition paths and
   actual endpoint selection/real COM execution. Original conditional service
   negotiation, channel/rate fallback, event/capacity checks, silence release
   and output allocation now compose with the matched-format native route
   cohort; full capacity can return success with zero requested quanta. Keep descriptor readiness, attachment success,
   frame lifetime and audible hardware output separate. Keep the separate
   Vorbis emulator/host and host/reference comparisons open. Close live allocation generations
   and provider buffers without bypassing voice/mixer admission. Reuse the
   audited source-bridge route when tracing the selected owner. The separate live join from the
   managed external path through its queued allocation into that native source remains open;
   repeated cookie values, timestamp order and cross-thread pointer equality do
   not establish allocation generation or lifetime. Request a new capture only
   for a concrete owner/carrier, provider/codec or allocation-lifecycle edge that existing
   recordings and selected native bytes cannot decide.
2. Re-derive the non-required catalog rows on the current build before enabling
   any of them; never reuse a superseded address.
3. With that session, test serial-versus-source-state-key equality through the
   importer's registration/join comparisons.
