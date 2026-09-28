# The native audio chain, and what a bounded capture would prove

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** The runtime side of the audio lane: how far the managed
external-source request is statically closed inside the selected build, which
read-only probes are prepared against it, and why none of them yet joins a key
to an opened file, a decoder stream, or audible PCM. It is the audio counterpart
of [`native_read_path.md`](native_read_path.md).

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
- **`externalSourceKey` is not a media identifier.** The external post carries
  key and path together, and one key names many files in one session.
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

**The hook that would settle it** sits above the family choice:
`CAkSource::SetSource(unsigned int, void*, AkMediaInformation)` binds a source
to in-memory bytes together with its media information, and
`CAkSource::LockDataPtr(AkMediaRef&)` is where a source resolves to the media it
plays. Either carries the source id and media identity in one frame -- the
key-to-file-to-decoder join. Adding it needs a new provider ABI, then a session.

## Eliminated readings

- `externalSourceKey` as a media identifier or a file-recovery key (one key, many files).
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

1. Add the `CAkSource::SetSource`/`LockDataPtr` hook ABI to the capture provider,
   then run one bounded session with voice; that decides the codec family and
   joins source id to media.
2. Re-derive the non-required catalog rows on the current build before enabling
   any of them; never reuse a superseded address.
3. With that session, test serial-versus-source-state-key equality through the
   importer's registration/join comparisons.
