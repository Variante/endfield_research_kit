# The native audio chain, and what a bounded capture would prove

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** The runtime side of the audio lane: how far the managed
external-source request is statically closed inside the selected build, which
read-only probes are prepared against it, and why none of them yet joins a key
to an opened file, a decoder stream, or audible PCM. It is the audio counterpart
of [`native_read_path.md`](native_read_path.md).

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
- **Codec argument: raw propagation, no conversion.** `Beyond.Audio.AudioCodec`
  (`PCM=-1`, `ADPCM=1`, `VORBIS=2`, `ATRAC9=6`, `OPUS_WEM=10`) flows unchanged
  from serialized `VoiceData.codec` through `RuntimeVoiceData.codec` and the
  adapter's typed parameter into `AkExternalSourceInfo.set_idCodec`, whose export
  stores it directly in the descriptor's codec slot. **It is not the public
  `AKCODECID_*` domain** (`PCM=1`, `VORBIS=4`, `ATRAC9=12`, `AKOPUS_WEM=20`).
  Native interpretation of the slot is open; the nearby sourceInfo/provider
  fallback field is a stream byte bound with no static edge from `idCodec`.
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

## Which codec path voice takes is open

SDK symbol matching (`scripts/game_data/wwise_sdk_symbols.py`, rows annotated on
every re-pin) shows three source families in this build: `CAkSrcFileBase` /
`CAkSrcFileOpus` (Opus streamed from a file), `CAkSrcBankVorbis` (Vorbis
resident in a bank or prepared media, no stream), and `CAkSrcMedia` with
`CAkSrcMediaCodecVorbis`/`PCM` (the media-source interface). The catalog's
three codec rows are the Opus file path and were never enabled.
`SourceProviderPreparation` is `CAkSrcFileBase::CreateStream`, and it recorded
nothing while voice posted, with no `.wem` opened. So either voice is not the
Opus file path, or the stream was created outside the window.

The next observation sits above the family choice. The reviewed
[`wwise_source_native.json`](../../scripts/game_data/contracts/wwise_source_native.json)
and [`wwise_source_native.py`](../../scripts/game_data/wwise_source_native.py)
now authenticate the three `CAkSource::SetSource` overloads, `LockDataPtr`,
their output-write helpers and two current managed post bridges against
explicitly selected native inputs. Historical SDK matches supply method
labels; the capture ABI and field flow come from the current instruction
bytes, not from an assumed SDK structure layout.

The memory/info overloads copy a pointer-backed 16-byte aggregate into the
source's first four words, retain their unsigned argument in a separate
source word, and the memory overload retains its pointer argument. The
scalar-only overload instead sets the source's first word and resets the
other observed fields. `LockDataPtr` chooses between a registry lookup using
that first word and direct pointer/count forwarding using a flag bit. Its
helpers write a bounded output reference containing pointers and a byte
count. A registry early return may retain the incoming reference, so observing
post-call fields alone does not prove a successful new lookup. None of these
facts makes the external cookie, SetSource scalar or lookup word interchangeable.

The same source contract now proves the anonymous owner behind an observed
direct-pointer `LockDataPtr` callsite. Its complete chained exception-directory
group resolves to the true function entry, rather than the interior segment
containing the call. Current instructions retain the entry owner pointer,
read its stored source pointer, and pass its embedded output reference to
`LockDataPtr`. Only a strictly audited pair at that authenticated returnsite
may project the owner from the captured output pointer and the contract's
member displacement. This is a conditional owner/source/output relation;
the owner was not independently sampled, and no SDK class, complete layout,
source lifetime or voice-file identity follows. Neither this caller nor
`LockDataPtr` reads the retained source argument into a codec selector, so that
word remains anonymous. The default minimal observer profile remains unchanged. An explicit
`--include-source-consumer` variant adds only the authenticated true entry
and fixed owner-relative source/output fields. It records the actual caller
and native parent lineage without interpreting a consumer return value or
following the source pointer. The classic and consumer recipes remain exact
generated profiles. Constructor/factory activation is outside those recipes;
transporting a preselected source pointer does not prove its selection or
lifetime. The optional source-bridge recipe below has its own additional gate.

The reviewed contract also closes one earlier static producer step. An
anonymous constructor retains its incoming source pointer and stores it in the
primary owner's member corresponding to the consumer's source member. It
addresses the embedded consumer owner explicitly and installs an address point
containing the reviewed consumer; the consumer's own reverse pointer adjustment
agrees with that storage relationship. One factory retains its incoming source
argument and forwards it unchanged to the constructor, passing a storage-provider
result as the primary owner. Current full code/unwind extents, bounded address-point
bytes, the exact consumer slot and instruction witnesses gate these facts.
They establish static transport of an already-selected source pointer, with no
allocator classification or source initialization/copy proof. In saved classic
and consumer recordings, constructor execution and producer address points were
not observed; those recipes activate no producer hook. Persistent lifetime and
the queued managed voice-path join remain open across all recipes.

The companion
[`wwise_source_queue_native.json`](../../scripts/game_data/contracts/wwise_source_queue_native.json)
and [`wwise_source_queue_native.py`](../../scripts/game_data/wwise_source_queue_native.py)
now authenticate the descriptor's earlier native transport and a conditional
selection route. The managed default body supplies the cookie and path through
checked setter order. Native copying retains the descriptor and its text in an
owned allocation, the event queue retains that allocation, and the checked
dispatch case carries it into the action's playback argument blob. The reviewed
node dispatch passes the same blob to a source selector. Its guarded branch
clones the incoming source, matches its stored word against a descriptor, and
prepares the selected source through the observed setter route. A checked config
address point then forwards the selected pointer through the already reviewed
factory and constructor before addressing the embedded consumer. Complete code
and unwind extents, transport instructions, dispatch-table bytes and actual
address-point targets gate this route; neighboring pointers supply no ownership
claim. The selector branch, preparation success and chosen address points remain
conditions, rather than observations of a runtime instance.

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

1. Reuse the audited source-bridge route when tracing the selected owner toward
   provider and codec setup. The separate live join from the managed external
   path through its queued allocation into that native source remains open;
   repeated cookie values, timestamp order and cross-thread pointer equality do
   not establish allocation generation or lifetime. Request a new capture only
   for a concrete owner/carrier, provider/codec or allocation-lifecycle edge that existing
   recordings and selected native bytes cannot decide.
2. Re-derive the non-required catalog rows on the current build before enabling
   any of them; never reuse a superseded address.
3. With that session, test serial-versus-source-state-key equality through the
   importer's registration/join comparisons.
