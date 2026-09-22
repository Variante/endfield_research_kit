# The native audio chain, and what a bounded capture would prove

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** The runtime side of the audio lane: how far the managed
external-source request is statically closed inside the selected build, which
read-only probes are prepared against it, and why none of them yet joins a key
to an opened file, a decoder stream, or audible PCM. It is the audio counterpart
of [`native_read_path.md`](native_read_path.md).

Every claim here is bound to one selected `global-metadata.dat` plus the
matching `GameAssembly.dll`, supplied explicitly. Missing or mismatched binaries
retain authored evidence but omit build-locked callsites, mappings and runtime
addresses. **The addresses, RVAs, offsets and branch tables themselves live in
the audio hook manifest and in the generated audits under
`reports/story/recovery/audio/`** -- notably
`native_registration_serial_audit.*`, the native-provider audit, and
`native_io_vtable_pointer_census.*`, which is static dispatch evidence and not a
runtime playback trace. Do not carry an address over from a previous installed
build, and do not restore module-global default game paths.

## The managed key is statically closed to the copied descriptor

- The VoicePlayer resolver's static arguments are closed on the selected build:
  it reads `VoiceI18n.s_languagePrefix` and calls the shared formatter as
  `("{0}/{1}/{2}", "Voice", languagePrefix, VoiceData.path)`, yielding the
  native key shape `Voice/<language>/<VoiceData.path>` before
  `PostEventExternal`.
- `_PostEventWithExternalSource` passes that same managed string directly to
  `AkExternalSourceInfo.szFile` before native descriptor copying, so **the direct
  VoicePlayer key-to-copied-descriptor path is statically closed**. The remaining
  runtime gap is source-state/sourceInfo instance selection and opened-handle
  identity.

## The codec argument is a separate closed boundary

- Current metadata defines `Beyond.Audio.AudioCodec` as `PCM=-1`, `ADPCM=1`,
  `VORBIS=2`, `ATRAC9=6` and `OPUS_WEM=10`, and the selected
  `_PostEventWithExternalSource` body forwards its eighth stack argument
  unchanged into `AkExternalSourceInfo.set_idCodec`. Its resolved
  `AkSoundEngine.dll` export jumps to a stub that stores the value directly in
  the descriptor's codec slot; **there is no setter-side conversion**.
- Current public `AKCODECID_*` constants use different values (`PCM=1`,
  `VORBIS=4`, `ATRAC9=12`, `AKOPUS_WEM=20`), so the raw Beyond enum domain is now
  closed at the descriptor while its downstream native consumer semantics remain
  unresolved. The installed runtime type table resolves both
  `RuntimeVoiceData.codec` and the adapter's codec parameter to
  `Beyond.Audio.AudioCodec`; the remaining gap is native descriptor consumption.
  **Do not equate the Beyond enum with the public `AKCODECID_*` constants.**
- The serialized side is closed too: `RuntimeVoiceData.FromSparkBuffer` and
  `VoiceData.get_codec` both read serialized `VoiceData.codec` through the shared
  SparkBuffer integer reader and copy the returned `Int32` unchanged into
  `RuntimeVoiceData.codec`, so that edge is **raw propagation**. The AudioDialog
  field name/schema agrees with that serialized field, but this does not claim a
  separate table-loader trace. Runtime type resolution closes the managed handoff
  into the adapter's `Beyond.Audio.AudioCodec` parameter; only native
  interpretation remains open.
- The nearby sourceInfo/provider branch is **not** that consumer: its
  non-flag-9 fallback becomes a provider state field that the selected stream
  helpers use as a byte-position/stream bound. The managed external `idCodec` is
  preserved in the copied external record payload and has **no static edge** to
  that provider field or to a decoder branch yet.

## Registration serial versus source-state key: comparison closed, equality not

- The external manager generates its keys from a lock-xadd serial slot and stores
  serial+1 on the registration record before the constructor retains it on the
  manager entry, while the two primary source joins load their key from the
  parent-B/source-state field. A complete audit of the source-state key writers
  finds **no store sourced from that serial slot**, so exact comparison is closed
  but equality is still a runtime-value question; path/handle and PCM handoff
  remain unobserved.
- The source-construction path does have an explicit static join: the same
  parent-B field is passed into the exact-key join, whose bucket walk compares it
  **directly** with the manager entry's serial, **with no hash transform**. A
  successful runtime match and the later file/PCM handoff remain unobserved.
- Within the child-source branch one source record is carried through a
  constructor that copies the record into the child object's key field, and the
  same record field is then used as the join key. This proves local same-record
  value identity, **not** an alias to the separately generated registration
  serial.
- An exhaustive direct-call census finds four join callsites: two in the primary
  source/voice construction paths and two in broader manager state transitions.
  Only the two construction callers carry the parent-B/source-state key
  explanation; the other two expand native join coverage but **do not** establish
  external-source media selection, path opening, or PCM delivery.
- An exact direct-call audit finds only two calls to the serial-generating
  helper, both in registration or external-post bridges, and the primary source
  setup calls only the exact-key join. This is **negative direct-call evidence,
  not proof that indirect or shared-record aliasing cannot occur**; the detailed
  census is kept in
  `reports/story/recovery/audio/native_registration_serial_audit.*`.
- Both constructor wrappers are covered by direct-call coverage; each prepares a
  native registration record before the constructor stores its dword on the
  manager entry. **This closes wrapper coverage but not equality with the
  source-state key.**
- The serial storage global's only references in the selected native `.text` are
  the lock-xadd writers, with no direct RIP-relative read at the source-state
  constructors, so **the source-state value is not statically shown to load from
  the serial global**.
- One local integer that looked like the key is not: the value assembled from
  temporary state/input plus a build constant and a context field is a different
  quantity. The source-state initializer copies its context field from the source
  config; one concrete producer fills that config field from an upstream record
  before the initializer runs, and two alternate constructors receive their
  config pointers through separate callers.
- The selected `.text` has exactly one direct source-config entry, whose stack
  argument comes from a record reached through a parent object. Because that
  result is parent B, the producer reads parent B's key field into the config
  before the source state is constructed. A sibling accessor reads the same
  parent-B field and two callsites pass it into a source vtable slot, **proving
  local field reuse**. This closes direct producer/callsite and local-field-alias
  coverage, but **parent B is not statically aliased to the external registration
  record or its serial**.
- The source-state metadata pointer is bounded separately: the initializer copies
  its incoming register into the metadata field and the config field into the key
  field, and the primary construction chain supplies that metadata pointer from a
  record produced upstream, while the two alternate initializer callers have
  separate metadata inputs. The external manager's descriptor allocation is
  retained on the manager entry instead, and **no direct selected-build edge
  joins it to that record or to the source-state metadata field**.

## The copied descriptor is retained as ownership, not as an input

- The retention edge is exact for the shared external PostEvent path: the copied
  allocation is received, stored in a local carrier, and a pointer to that
  carrier is passed on; the callee copies the carrier's 0x14-byte descriptor
  payload into the registration record, a forwarder passes the record field on,
  and the constructor stores its first qword on the manager entry. So **that
  manager field is the copied external-descriptor allocation pointer in this
  path, not a raw UTF-16 string.** This still does not join that allocation to
  the sourceInfo descriptor field or to the source-state key at runtime.
- The retention lifetime is bounded too: the exact-key detach callers reach a
  routine that reads the manager's descriptor field **only** to pass the
  allocation to refcount release before unlinking the entry. It does not
  dereference that field as a path and does not feed the provider or the codec,
  so the field is an **ownership-retention field rather than a direct
  sourceInfo/provider input**.
- The exact join body is narrower than a media lookup: a hit appends the
  source-state pointer to the manager entry's attachment array and updates its
  count and capacity, optionally retaining auxiliary state. It does not read the
  manager's descriptor fields or the copied UTF-16 record, so **this edge is
  lifecycle/state registration only**; the runtime key match and the separate
  provider-to-path/handle/PCM handoff remain open.
- The joined source-state pointer is retained only as manager-entry attachment
  state: one routine appends it, another removes a matching pointer and
  decrements the count before invoking the release path, and manager reset frees
  these arrays. **Those consumers are lifecycle cleanup, not path/byte reads or
  codec input, so a join hit does not itself select a media file.**
- The sourceInfo file/key descriptor path is statically bounded through the
  concrete factory, whose constructor installs a secondary vtable on the
  allocation; its descriptor-copy path carries the descriptor's first field as a
  UTF-16 path into provider-owned storage. The selected factory's provider slot
  copies that field into provider-owned UTF-16 storage and retains two further
  descriptor metadata fields.
- A separate source-state helper feeds the sourceInfo's leading word and a
  bit-extracted field into a selector through a global slot; the selector walks
  its own table and compares an entry field to the sourceInfo word. That slot is
  **distinct** from the external-manager hash slot and from the decoder registry
  slot, so **the sourceInfo word is bounded as an internal selection key rather
  than a proven registration serial**. The selector's helper fills a 0x20-byte
  descriptor of matched entry, optional type-2 context and two candidate fields;
  the caller checks those against a source field, passes the candidate through a
  helper, then applies sourceInfo before copying the descriptor into the source
  object. **This joins the internal key to source/provider setup, but runtime
  values, path/handle choice and PCM delivery remain unobserved.**

## Provider to file, and provider to decoder

- The provider input boundary is separate from registration: the preparation
  routine loads the owner and its sourceInfo, and its file/key branch chooses the
  sourceInfo descriptor field for the local descriptor **when flag bit 9 is
  set**, then passes that descriptor through the singleton provider vtable to
  provider-owned UTF-16 storage. That call boundary carries no manager entry, no
  manager descriptor field and no source-state key value, so it **closes
  sourceInfo-to-provider provenance while leaving identity with the copied
  external descriptor unresolved**.
- Static analysis joins the file/key provider secondary interface's
  GetBuffer-shaped queue to the registered device and to the device's default
  file-I/O request slots used by `PerformStreamMgrIO`; the adjacent provider slot
  is release/advance-shaped.
- The provider-to-file boundary is explicit: the open wrapper passes the
  registered-device descriptor and returned path pointer through two helpers; the
  default I/O table dispatches its first slot to a routine whose
  `CreateFileW`/`GetFileSize` pair stores the handle and size, and the second
  helper chooses the incoming path or the device base path and normalizes it.
  This **closes provider-request to native-open transport**, but the boundary
  still carries no external key, source-state key, or manager descriptor value.
- The Wwise default-I/O path is hooked at its real function entry (the manifest
  decodes the UTF-16 file-path argument); **do not treat the interior branch as
  an independent function.**
- The registered-device pump selects the provider and assembles each 0x18-byte
  request descriptor before dispatching the registered-device subobject. The
  provider's primary vtable has an active ordinary-path slot that can create a
  chunk/request; its **secondary address point is only a provider field
  serializer and does not populate the pump's candidate-context or flag slots**.
  On the accepted ordinary branch the pump forms the request descriptor's second
  field as the *address of* the candidate's second field (`lea`, not a
  dereference), and the carrier's branch-dependent provenance remains unresolved.
  The subobject's first three slots resolve to open, setup and release, **not**
  the later batch-read slots; the same device vtable separately exposes direct
  `ReadFileEx` and `WriteFileEx` slots on its primary address point. The active
  composite address point retained at the stream manager resolves its slots to
  provider/state dispatch, direct `ReadFileEx` and `WriteFileEx`, so **the pump
  makes a static provider-preparation -> `ReadFileEx` join**. Each batch-read
  writes only its internal helper into the request; it does not initialize the
  request's callback field, so **callback ownership remains upstream**.
- The pump's provider virtual call passes an explicit descriptor output slot, a
  candidate context slot and a flag slot. The active implementation initializes
  those outputs and may create the request; the alternate serializer only writes
  provider descriptor fields, and the state-2 helper instead enters the
  default-I/O filter/deferred callback path and does not initialize the
  pump-local context slot. **Thus the candidate-carrier source is a conditional
  provider-to-request edge, not a closed provider-result proof.**
- The same plug-in exposes an alternate provider-batch wrapper that filters
  provider pointers and calls the device dispatch helper. Inside the read routine
  the descriptor ABI is exact: 0x18-byte stride, the descriptor's first field a
  provider object whose handle carrier holds the `ReadFileEx` handle, and the
  descriptor's second field the ordinary carrier at request base + 8. For a
  request base the carrier fields are, in order, the request base + 8, the byte
  count, the caller-supplied buffer/source, a fixed callback, and the read ring
  helper. The provider-dispatch-to-active-pump address point calls the read
  routine directly after filtering, which **closes the active
  provider-to-`ReadFileEx`-to-request-recycle transport without claiming a live
  key-to-file or PCM mapping**.
- Static dataflow identifies that provider object: one routine allocates the
  0x70-byte state record and stores a queue/state callback and the owning source
  object in it. So the device helper's provider callback resolves to a
  **queue/state transition, not the codec stream object's indirect callback**.
  The source-manager constructor installs the primary vtable at the 0x110-byte
  allocation base and the secondary vtable at an interior offset; the decoder
  receives the secondary interface while the request retains the primary base.
  Together with the pump's direct read call on the active address point, this
  **closes provider-to-`ReadFileEx`-to-request-recycle into the same codec
  provider allocation**.
- The request constructor takes a free-list object from the stream manager,
  writes two request fields, stores the caller's register as buffer/source, and
  installs the fixed callback, self, and the primary provider base. The pump
  passes the candidate's second field, so completion loads the carrier's callback
  field and tail-jumps to that fixed callback with the carrier as `this`; **that
  completion therefore sees the same provider allocation whose secondary
  interface supplies the codec queue.** Two further callers supply
  branch-specific source/offset inputs to the segment allocator; **neither adds a
  new stream descriptor beyond the two codec paths**.
- The provider-to-decoder handoff is exact for the concrete decoder class: the
  refill routine calls the provider's buffer slot, then the decoder's own slot,
  which the decoder address point resolves to an implementation that stores the
  provider buffer on the decoder and updates three adjacent fields. Refill and
  reset release through the provider's release slot. **This closes buffer
  ownership into the decoder and joins `ReadFileEx` completion/request recycle to
  the same provider allocation and queue.**

## Decode output, and the bounded negatives around it

- The selected decoder output path is statically closed: the caller calls the
  decoder, loads the returned float samples, scales and converts them, and writes
  **signed PCM16** samples to the caller-owned output buffer.
- The selected Opus descriptor and the header-recognized generic memory
  descriptor are both resolved: a three-hop construction path builds a descriptor
  whose four entries are copy/advance, seek, data-pointer and free.
- A selected-build direct-call scan finds **only two** calls to stream setup: one
  from the Opus wrapper with its own descriptor, and one from the generic memory
  wrapper with the four-entry descriptor above. **No additional direct setup
  callsite or direct descriptor literal is present; an address-taken indirect
  caller would remain outside this scan.** A raw scan also finds no absolute
  pointer literal or RIP-relative memory operand resolving to either the
  stream-setup or the codec-stream-callback address, **excluding an in-image
  static setup reference while leaving runtime-computed or external pointers
  open**.
- The optional decoder callback context field is *read* at one callsite but has
  **no direct store** in the current `AkSoundEngine.dll` function table. A
  direct/overlap-aware audit of selected `.text` operands covering the
  surrounding 0x20-byte window finds writes at two nearby dwords and a qword
  ending one byte before the field, **with no write reaching it**; this is a
  **bounded negative result, not proof that indirect initialization never
  occurs**.
- An exhaustive direct-call census finds **ten** valid readers of the codec
  stream callback, grouped in seven containing functions. This **closes the
  direct read-consumer census but does not identify additional setup descriptors
  or indirect callback targets.**
- The matching census finds **three** valid callers of the decoder: one whose
  returned float samples flow through the known signed-PCM16 writes, plus the
  initial attempt and the retry after provider refill, with return codes driving
  decoder state and consumption. **No other direct decoder call exists in the
  selected `.text`**; this expands decode-consumer coverage without proving an
  indirect decoder target or a new PCM sink.
- The profile also observes the embedded codec stream callback, including its
  indirect callback/context pointers and bounded buffer state, plus the selected
  Opus memory-source copier. Every direct parser caller supplies a known callback
  in the callee-frame slot, and both such callbacks are **integer-array
  transforms, not PCM sinks**.
- The native manager-constructor status return is decoded: one value is the
  successful registration path and another is the allocation-failure path in this
  build. The importer records `registrationStatuses` so a future capture can
  distinguish a missing join from a registration that never completed; **status
  alone does not prove source-state, file, or PCM identity.**
- The source-manager callback branches are explicit: two branches each require
  their own object flag bit, write cookie/context/key/aux into a resolver or
  stack descriptor, and invoke the callback with their own operation code, one of
  them storing the return on the manager. The fixed bridge maps one operation to
  its no-op path and the other to the queued callback record. **This is callback
  descriptor transport only; managed path, opened handle, and PCM ownership
  remain open.**
- The adjacent exact-key branches are bounded the same way: each requires its own
  entry flag bit, sends entry cookie/context/key/aux to the stored callback with
  its own operation code, and is reached from a known set of callsites; the fixed
  bridge maps one to the common queued record and the other to its
  string-or-generic queued-record builder. **These remain state/notification
  transports, not file selection, handle opening, or PCM handoff.**

## The prepared probes, and what an authorized capture would add

The audio hook manifest verifies `AkSoundEngine.dll` and attaches optional native
lookup, source-manager key-join, key-to-decoder registry, source/provider
preparation, post-call descriptor, callback-queue, Wwise open and
asynchronous-read probes, plus the managed external-post/callback boundaries.
**These hooks are prepared evidence only until an authorized capture observes a
match**, and no verified capture has produced the decoder continuity rows yet.

- An optional current-build `VoicePlayer.ExternalSourcePreparation` hook records
  the formatted `externalSourceKey` together with the Event, audio-object
  argument and voice handle immediately before the external-post helper, and
  samples its `codec` stack argument as `voicePreparationCodecs`. This narrows
  the managed path-resolution boundary, but **does not by itself prove native
  lookup, file open, decode, or audibility.**
- The key-join probe records the requested key and the source-state key field;
  the registry probe records the same key argument and the active decoder
  pointer.
- The provider-preparation hook follows the decoder's owner chain and records the
  descriptor's UTF-16 candidate **without assuming that its flags select the
  path**; the importer reports only exact path-string overlap with the
  default-I/O open hook.
- The descriptor-copy hook records the copied allocation pointer and the
  manager-constructor hook records its `descriptorInfo` pointer; the importer
  publishes `sharedDescriptorAllocationBases` when a same-session pointer match
  is observed, **without promoting it to a sourceInfo, file-handle, or PCM
  join**.
- The source-manager constructor hook decodes its stack ABI explicitly: the
  resolver function stored on the manager, the mapping pointer, and the operation
  flags.
- The runtime manifest hooks the exact decoder entry ABI `(decoder, float-output
  slot, frame-count slot)`. It samples the decoder owner's source-state key, the
  provider interface, the returned float-buffer pointer, the produced frame
  count, and the native return address before and after the call; one return
  address identifies the direct caller whose static body writes PCM16 and the
  other two are the refill/retry callers. The importer reports
  key-registry/decoder-call, source-provider/decoder-call and
  source-state/decoder-call intersections as **bounded continuity evidence**, and
  compares the provider-preparation `sourceOwner` with the decoder-entry
  `decoderOwner`, giving a same-owner check for the sourceInfo/provider instance.
- The optional sourceInfo-selector hook samples the post-call selected table
  entry key, the candidate descriptor pointer and a candidate auxiliary field.
  The source-info consumer and provider-preparation hooks sample the source
  object's copied descriptor pointer after the consumer returns. Matching these
  pointers is a **bounded selector -> source-owner continuity check; it still
  does not identify the external file, handle, or decoded PCM.**
- The optional source-state initializer hook samples the destination source-state
  object, the incoming source config field, the incoming `sourceInfo`, and the
  post-write key and metadata fields. The importer intersects those objects and
  keys with manager joins, provider owners, decoder owners and sourceInfo
  pointers. **These are initialization-continuity checks, not proof that the
  managed external key selected that instance.**
- The audio runtime trace reads the default-open routine's provider context after
  the call: the selected build stores the `CreateFileW` handle and the file size
  in that context, and the async batch descriptor's provider object is sampled
  the same way, so `runtime_trace_audio_import.py` reports an exact `openHandle`
  / `descriptorProviderHandle` intersection when one capture shows the same
  native handle crossing open into `ReadFileEx`. This is **stronger than a path
  string overlap, but it still does not prove source-key ownership, decoder
  selection, PCM delivery, or audibility**; stack-memory capture is enabled only
  for this verified native hook contract.

### What the importer publishes, and the ceiling on each relation

- `nativePairing.keyLifecycle` carries bounded key intersections, explicit
  `registrationManagerJoinRequestedKeys` /
  `registrationManagerJoinStateKeys268` comparisons, descriptor paths and
  file-open paths. Those registration-to-join intersections **directly test the
  currently unresolved generated-serial versus source-state-key equality**, but
  remain same-session evidence unless pointer or managed call-chain data narrows
  them to one request; they are **still not proof of one handle, codec stream, or
  PCM buffer**.
- The Frida agent resolves the exact external-source manager hash-table node by
  serial at constructor return and at join/lookup entry, and the importer exposes
  `registrationManagerEntryPointers`, `managerJoinEntryPointers` and
  `sharedRegistrationJoinEntryPointers` plus the lookup equivalents. A shared
  pointer proves that the observed values reached one native manager entry **in
  that capture**; it still does not prove the descriptor selected a file handle,
  decoder stream, or PCM buffer.
- `managerEntryDescriptorInfoPointers` and
  `sharedManagerDescriptorAllocationBases` compare the manager entry's
  descriptor field with the descriptor-copy allocation, **proving retention of
  the same descriptor allocation when they intersect; this remains ownership
  evidence, not a sourceInfo/path/file/PCM join.**
- Each native hook event carries `nativeParentCaptureId` when another attached
  native hook is active synchronously on the same thread, and the importer
  publishes exact resolved pairs under `nativePairing.nativeCallRelations` as
  `synchronousNativeHookNesting`. Missing or merely adjacent IDs are omitted, so
  **this relation does not infer asynchronous ownership, file, decoder, or PCM.**
- `nativePairing.managedExternalPathLifecycle` joins the optional VoicePlayer
  preparation path to the Adapter external-post path **only through the Frida
  parent-capture chain**, then compares it with descriptor/provider/open path
  strings in the same session. Exact parent/path matches narrow the
  managed-to-native boundary but are **still not a native handle, decoder,
  branch, or PCM correlation.** Native events also carry the same-thread managed
  hook stack when a synchronous bridge is active, and the importer emits bounded
  `managedNativeContextCorrelations` plus exact descriptor/provider/open path
  matches for that direct stack relation: **stronger than a same-session string
  overlap, but still not a join to a later asynchronous sourceInfo, handle,
  decoder stream, or audible PCM result.**
- `nativePairing.callbackLifecycle` records bounded callback-context transport
  evidence when the native resolver/queue descriptor pointer equals the managed
  `_OnExternalSourceEventCallback` cookie. **That pointer is the temporary
  callback mapping object, not the Wwise external-source cookie**, and the match
  still does not prove file, decoder, PCM, or audibility. When the managed
  parent-capture chain includes `AkCallbackManager.PostCallbacks` and
  `_ProcessEventCallback`, it also emits bounded `managedExternalCallbackChains`
  and raw callback-type values, which **prove the managed Wwise
  callback-delivery chain for that capture only**; it does not join the native
  resolver descriptor, file, decoder, or PCM.
- Native rows are **execution evidence only**. The importer does not claim the
  native key-to-provider path or the decode mapping until one capture correlates
  the external descriptor and opened path with the selected stream callback and
  the resulting decoded data flow.

## The catalog is the host's input, and re-pinning it is gated

`audio_runtime_trace_hooks.json` is an evidence catalog: 64 rows pinned to the
build they were recorded on, of which the capture host requires **five**.
`StartCapture.bat` pointing `BUILD_MANIFEST` at it is correct -- the host reads
this schema -- but the path had not followed the `scripts/` reorganisation, and
the pin was a superseded build.

**The host owns the conversion, not this repository.** It looks the five hooks
up by name in the catalog, takes only each one's `rva`, supplies the module and
ABI identifier from its own table, and writes the `activation.v1` manifest the
provider consumes. Producing an activation file here writes something nothing
reads -- a mistake worth recording, because the catalog's own integration note
describes the conversion and it is easy to assume the conversion is ours.

What actually blocks a capture is the catalog's build pin, and
`scripts/webui/story_recovery/refresh_audio_hook_catalog.py` re-pins it,
verifying the two halves differently because they are different claims.

**The managed halves are re-resolved and they moved.** `AudioAdapter._PostEvent`
and `_PostEventWithExternalSource` live in `GameAssembly.dll`, so their
addresses come from `il2cpp.method_resolver` by name against the selected
build. They moved -- `0x328a690` to `0x337f270`, and `0x3abea70` to
`0x3fa4a80` -- so carrying the recorded values forward would have attached two
hooks to the wrong code.

***The native halves did not move, and that is checkable rather than assumed.***
`AkSoundEngine.dll` was rebuilt: same 3,586,536 bytes, different SHA-256. Its
RVAs are nonetheless still valid, and the evidence is the binary's own `.pdata`
exception directory, where a `BeginAddress` *is* a function start by
definition. **29 of the catalog's 32 native rows land exactly on one**, at a
density of one function per 212 bytes of `.text`; the three that do not are
sixteen-byte leaf getters, which MSVC omits from `.pdata` by design. The
generator re-checks each activated native RVA against that table and refuses
the whole manifest if one is not a function start, so a future rebuild that
*does* move code fails closed instead of attaching a hook to whatever now sits
there.

That asymmetry is the useful part: a rebuilt native DLL is not automatically a
re-derivation job, and a rebuilt `GameAssembly.dll` always is.

## A capture cannot name an Event, and what it can do instead

Worth stating exactly, because the opposite is easy to assume. The audio
provider's post hook is
`(uint32 eventId, uint64 audioObjectId, uint32 callbackType, ...)` -- it
carries the hash and never the spelling -- so **no session run with the shipped
hooks names a hash-only Event**. `AudioManager` does expose string overloads
(`PostEvent(string)`, `PlaySoundAtPosition(string, ...)`,
`PostAudioCue(string)`), so a *different* hook could observe a name, but that
hook does not exist and building it would only reach names that ship as
literals, which the static sources now read far more thoroughly.

What a session can do is the continuity this file is waiting on, and
`scripts/webui/audio/semantics/runtime_capture_import.py` is the consumer side
of it. It validates a session against the provider's own counters in
`audio/summary.json` -- dropped records, unpaired calls, a window still open at
session stop, an incomplete session -- and refuses the whole session naming the
gate rather than reporting a smaller number across a hole.

**The payload layout is recovered, and it is the writer's own.** The
per-callback records ship as opaque `payloadHex` blobs whose layout is not the
in-memory `CallbackRecord` -- the payload is 208 bytes where that struct is
larger. It is `AudioEventPayload` in `runtime_dll.cpp`: five u64, four u32, a
kind byte, then a 48-byte hook name and a 96-byte key/path, summing to 201 and
padding to 208. The decode is self-checking and checks out: across a real
session every payload decodes, the hook-name field resolves to exactly the
three constants the adapter declares, and calls and results pair one to one.

***A session already on disk carried observed playback that nothing had
read.*** Over 32.7 seconds of windowed capture: 693 calls and 693 results with
**no unpaired call and no truncated text**, **111 distinct Events posted** in
689 posts each returning its own playing id, and **19 of those Events have no
recovered name** -- so they are genuinely hash-only *and* genuinely used, which
authored evidence alone could not establish.

The four opened paths are the same bank probed in order across
`Persistent` and `StreamingAssets`, each with and without the `Chinese`
subdirectory. That is the overlay fallback rule of
[`../game_data_recovery.md`](../game_data_recovery.md) observed at runtime
rather than inferred from the catalog.

**What is still not joined.** Posts, prepared source keys and opened paths are
counted separately. A key seen at two hooks in one session is a coincidence of
numbers until ordering and identity are checked, and the key-to-file-to-decoder
continuity therefore remains open: this session prepared no source keys at all,
so it cannot speak to it.

## What remains unresolved

The remaining address-taken codec callback/initialization targets, callback
ownership, runtime external source-state/sourceInfo identity, and live
invocation. Fixed-callback provider identity is closed, the two statically
reached stream descriptors have resolved `+0` stream callbacks, and the direct
VoicePlayer external key-to-copied-descriptor path is statically closed. What is
left is a **live** key-to-provider path invocation and the
source-state-to-provider path correlation -- which no static reading can supply.
