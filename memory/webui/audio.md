# Audio page recovery

## Purpose

Audio is an evidence browser over decoded media, Wwise Events, authored
consumers, semantic controls, and bounded runtime observations. It also stores
user research notes without modifying generated evidence.

## Inputs and recovery flow

1. AnimeStudio reads AKPK/Wwise payloads from StreamingAssets with Persistent
   overlay/fallback and decodes lossless FLAC directly.
2. `scripts.webui.audio.build_audio` owns decode, Wwise bank indexing,
   Event-to-media traversal, Story relinking and Gameplay sound sidecars. Known
   HIRC Event categories are resolved before decode, so media land in their
   final category folders; its module docstring holds the layout and cache
   rules.
3. The same command runs the internal semantic orchestrator
   (`build_audio_semantics.py`), whose reusable evidence owners live under
   `scripts/webui/audio/semantics/`.
4. Optional verified runtime-trace bundles add matching observed request
   relations and a separate bounded external-source request summary.
5. `webui/overrides/audio_notes.json` stores searchable manual notes through the
   local server.

Story relinking reads Story's published `conv/*.json` and writes only Audio's
own sidecars: the relink owns their line, conversation-event and cutscene
fields, the semantic refresh owns the dialog lifecycle hooks, and each replaces
only its own. Without published Story, Audio builds and links no voice lines.

## Primary generated outputs

- `webui/data/lang/<LANG>/audio/{index,events,media}.json` plus lazy semantic
  shards and `scene_backgrounds.json`;
- `webui/data/lang/<LANG>/gameplay/sound_effects.json` and the other Gameplay
  audio sidecars;
- `webui/data/lang/<LANG>/audio/conv/<key>.json`, merged by the Story page;
- decoded media under `game/Audio/shared/` (SFX/music) and
  `game/Audio/<LANG>/` (voice).

Heavy direct-effect records, including anonymous native input reads, live in
lazy media detail shards. Bus effect parameters remain in the shared unique
Bus catalog and are resolved through authored output/auxiliary Bus paths.
Convolution definitions can be reached through an Event's authored auxiliary
Bus path. Mastering Suite's recovered reads currently remain definition-only:
the published Event/media graph contains no serialized reference to those
definitions, so they have no row-specific disclosure or media ownership. A
decoded definition does not create a playback edge; a future exact effect-slot
reference is required before its reads appear on an Event or media detail.

## Evidence boundary

- Media identity, Wwise graph relation, authored consumer, runtime request,
  selected branch and audibility are separate layers
  ([`../game_data/audio_overview.md`](../game_data/audio_overview.md)).
- Event traversal and authored control curves do not prove live values or DSP
  response. A prefab source does not prove a scene instance.
- Selector-to-media joins retain the full package path, bank ID and Sound
  object ID. A legacy package basename needs a unique full scope in the Event
  evidence. Missing or ambiguous scope keeps candidate IDs and an explicit
  package-identity diagnostic instead of a direct link. Different base/hotfix
  bank bodies and their ordered Event actions remain separate authored records.
- Runtime bundles must pass source, build, language and terminal validation;
  otherwise they stay degraded and create no binding.
- A lossy native entry session remains diagnostic material even if its manual
  window closes correctly and its saved entry IDs are contiguous. Audio's
  callback-loss receipt covers the whole attached lifetime. Retain the prior
  admitted publication while investigating the recorder and static caller
  paths; surviving rows do not establish complete-window counts or new links.
- Story-line binding can close purpose investigation for a media record, but
  does not prove playback in a captured session.
- Manual notes are user annotations and never upgrade confidence.
- A decoded `soundEvent` member is a naming candidate even when it carries prose
  or outer whitespace; the page gains an Event name from it only on a selected
  HIRC Event-object hash match, and other authored references stay visible with
  `foundInWwise=false`. Use `decodedPayloadEventNameRecovery.promotedNames` or
  the final `eventNames`, not the raw `eventNameSources`, to tell whether that
  source supplied an identity.
- Exact SkillData/BuffData PlaySound actions stay in the Gameplay sound sidecar
  with raw literals, action paths, frame/event slots, native enum labels and
  typed target settings; only HIRC-matched actions join Event contexts, and an
  unlinked Buff action can show its trigger slot without gaining an owner.
- The selected `PlayVoiceNarrative` LevelScript reader now proves a stored
  `voId` voice key and `voiceHandle` output path in a ledger-joined source.
  The Audio page's authored voice-path relation remains separate from event
  execution, a produced handle, and audible playback.
- A verified generic runtime bundle can publish bounded managed external-source
  request paths and cookies in the Audio runtime summary. A captured path is
  an observed request argument. The current decoded index retains a shortened
  dialog path rather than the complete original VFS source path, so this
  summary does not bind a media row by reconstructing a prefix, matching a
  basename or equating a cookie with a media id. A sibling anonymous-source
  panel shows separately audited source pairs, flag states, and verified
  synchronous consumer-to-LockDataPtr nesting. Publication replays the exact
  saved trace, diagnostics, and profile against explicitly selected native
  inputs. A missing, mismatched, or changed input withholds that panel's claims.
  A bounded native-selection detail can also show captured descriptor text,
  its cloned source, the constructed anonymous owner, and its consumer/Lock
  relation within one verified same-thread selector interval. Counts cover
  the audited capture; bridge, consumer and optional owner/carrier representatives share one display
  budget. The text remains an observed native argument, without a link to a
  decoded media row or a claim that its backing file opened or decoded.
  These native summaries never annotate Event or media rows and leave the
  asynchronous managed-path-to-source/provider join open.
  Current live capture uses EndfieldCapture's separate `audio source-owner`
  entry-only recipe. A complete retail session now supplies a separate
  `nativeEntryObservations` Runtime detail: counts include unobserved hooks,
  native texts stay grouped by entry hook, and source storage fields retain
  their local snapshot boundary. It does not merge entry counts into paired
  source relations. The native entry audit cannot
  supply result snapshots or same-thread parent nesting to the generic paired
  projection. New native carrier entries need their own complete-session
  admission before publication; no name/pointer/time proximity bridge is added.
  The combined `audio source-provider` selection adds local decoder
  preparation, ordinary/alternate factories, ordinary open dispatch and
  descriptor-input entries to the same independent detail. A complete retail
  session now supplies these entries and full voice-path inputs. Its optional
  `providerEntryObservations` detail shows independently authenticated caller
  roles and local provider/factory address-point matches. The observed factories
  use source-based preparation; decoder preparation was unobserved in that
  window. A failed dispatch gate withholds this child while preserving admitted
  base entries. Distinct representative voices share one capture window;
  repeated plays and separate per-voice sessions are unnecessary. Input text
  and an open-dispatch entry do not prove that storage, file opening, decoding
  or output succeeded.
  The `audio source-io` variant adds retained provider text/device
  snapshots and external-package path/key lookup inputs to the same entry-only
  lane. Its independent native gates and activation version keep prior saved
  recipes replayable. A complete recording now supplies these inputs. The
  optional `ioEntryObservations` child shows local retained descriptor/device
  states, a matching default package I/O address point, authenticated hash
  callers and independent lookup-key/table-count cohorts. Full-width keys are
  decimal strings to preserve their precision in the browser. Path/key equality
  is a cohort comparison, not a call chain or selected package/media binding.
  The expanded recipe now admits package-completion entries with separately
  gated local request/result equality, incoming success status and descriptor
  geometry. External-path samples also compare their computed key low word and
  modulo-width byte offset. The entire window is summarized before the display
  budget: repeated descriptors are counted together and text-bearing samples
  appear first. Earlier source-I/O recipes cannot supply completion fields. Each representative can be played once
  in the same window; package lookup fan-out does not require repeated playback.
  The expanded activation preserves those entries and adds default read-batch,
  platform completion and pre-transform observations in one window. Its
  independently gated `packageReadObservations` child now has an admitted
  complete recording. It separates platform error/transferred-byte inputs
  from local descriptor/cookie comparisons and keeps the buffer-word sample
  distinct from decoded PCM. The whole window is grouped into descriptor
  geometry cohorts before the display bound, with transform-range unions and
  distinct sampled-word counts. The selected voice's ranges span its descriptor.
  Optional indexed encoded-word comparisons match the sampled words across
  voice and numeric/background cohorts. This is a bounded candidate-index
  comparison, without live filename, pointer-generation or complete-buffer
  claims. Representative buffer words stay in a nested disclosure so the
  complete-window range and package comparisons remain easy to inspect.
  The observed-coverage disclosure counts encryption flags, relative offset
  alignment/origin and descriptor-range classes over the full admitted window.
  Stratified representative selection exposes its represented/total strata and
  preserves hook/interface/check-outcome diversity within the display limit.
  These counters measure the recording, not prevalence across installed files;
  repeated observations of one path cannot close an unobserved branch. A
  prepared receiver profile is available, but another single-voice recording
  is deferred under the corpus-first capture policy.
  The static proof now includes the embedded-transfer initializer, producer
  transport and conditional primary-provider and separate queued-receiver interfaces. Their request
  state updates and downstream wakeups stay distinct from decoding. The single
  Audio command can refresh this independent evidence disclosure directly in
  an existing current publication, with schema/language and concurrent-write
  guards, so further capture analysis does not require a broad semantic rebuild.
  Historical source profiles match maintained operational recipes exactly;
  descriptive evidence prose may change while retaining its declared key/type
  shape. Published claims always come from the current gated audit, never the
  saved profile's prose. The focused runtime-source refresh reuses only the same
  published bundle path and digest and preserves independent observations.
  A separate managed request/result disclosure recovers the already recorded
  Event ID, audio object, external path and returned playing ID. It does not
  pair those requests with asynchronous reads. The adapter's Event ID is not
  an external cookie or package key; old importer scalar labels were corrected.
  The optional offline-decode disclosure displays selected numeric-entry PCM
  comparisons and their channel/rate/duration metadata. Its independent receipt
  checks current inputs without decoding again; these results remain historical
  offline comparisons, separate from game-side PCM or Event selection.
  The owner/carrier detail requires its own authenticated entry-only profile
  and fresh strict replay. It shows local decoder-owner snapshot equality at
  a control handler, with nullable decoder slots and fixed source fields.
  Entry snapshots are not atomic, do not prove an internal branch or decoder
  creation, and cannot inherit a previous selector's pointer generation or path.
  Stored source data stays an anonymous pointer without text or media links.
  Interrupted recordings remain diagnostic archives. Even paired rows and a
  recorded target voice cannot replace the strict clean-stop receipt; keep
  existing validated publication until a new import passes. Missing carrier
  rows in such an attempt establish no negative playback/backend claim.
  A separate static provider-preparation detail shows authenticated
  decoder/owner/source reads, conditional pointer-versus-word transport and
  the anonymous source-argument halfword. Its selected-build gate runs without
  a runtime trace and publishes no claims on missing or mismatched inputs.
  A separate storage gate adds conditional ordinary-versus-alternate output
  interfaces and owned UTF-16 text copying under the reviewed singleton
  initialization. Storage failure withholds these claims while preserving
  authenticated preparation. The detail cannot establish a live provider, codec, opened file, live
  request continuity or audible output, and never annotates Event/media rows.

### What each rendered state refuses to claim

The independent static package inventory now appears before runtime captures.
Its current-roster gate covers available packages, including hotfix entries,
and exposes typed key duplication and external-key low-word collisions. It
keeps stored package identity separate from decoded-output provenance and live
package selection. The compact page projection never turns these keys into
Event/media links; exact inventory and changing counts remain in the raw gate's
generated report. This recovery lane runs offline and needs no sound playback.
Package rows also expose bounded previews of their own stored language tables,
with truncation marked explicitly. Summary label counts use exact labels only;
undeclared IDs remain unresolved. These labels do not establish spoken language
or runtime selection, and the complete tables remain in the raw corpus report.

The frontend renders these tokens verbatim (listed in the header comment of
`webui/src/features/audio/index.js`):

| state | does not claim |
| --- | --- |
| Music Switch tree paths (type `0x0C`, from `musicNodeEvidence`) | live group values, the selected leaf, audible output; a missing same-bank declaration is a local join gap. Rows need argument-only `pathKeys`, so an older shard that still carries the root sentinel shows no rows until a focused HIRC refresh |
| `monoBehaviourAudioIdField` role | any field executed, posted, selected or audible |
| Spawner pre-warning rotation | in-game placement; shown only when the nullable Vector3's presence flag is set |
| prefab source row | a level instance; `sceneId`/`sourceName`/`sourcePath` only on exact containment, `conflictingPrefabInstanceIdentityJoins` on disagreement |
| grammar-hash-preimage name | caller, trigger, execution, branch or audibility; only the owner and category its spelling encodes |
| authored-payload-literal name | a consumer, trigger or playback location: the spelling is exact, the holding field is unidentified |
| `noExplicitOutputBusSerialized` | default or parent routing, silence, or an effect-free path |
| `ownerKind=npc` | a single owner for a mixed Event (the NPC stays on occurrence/Clip evidence) |
| namespace and native-response groups | speaker choice, Wwise selection or playback location; shared media list every owner |
| AudioCue AST | condition truth, variable value, handler dispatch, cue execution, branch selection |
| `controlCatalog.staticRtpcAlignment` | current names when the gate is missing, mismatched, malformed or stale; `0x1802`/`0x1804` are never renamed |
| effect chain, RTPC, State, Aux-send, ducking rows | runtime DSP order, effective inheritance, live values, branch selection |
| built-in effect parameter names (`effectParameterNativeGate`) | shown only after the selected native triplet validates; Convolution Reverb and Mastering Suite show an expandable `structuralOnly` table of anonymous input read offsets, widths, read kinds and raw bytes. Scalar loads can have a float32 representation view, without a control name, unit, transformed value or runtime DSP role. Short blocks and malformed partitions show `failedClosed` diagnostics and no read rows; unread suffixes stay explicit. RoomVerb's private floats have no use-role label; a missing gate shows unverified; no live activation |
| `runtimeObservations.externalSourceRequestsStatus=ready` | a captured managed path/cookie request; no exact decoded-media binding, native-source ownership, file/codec choice or audibility |
| `runtimeObservations.nativeSourceObservationsStatus=ready` | anonymous source fields, verified same-thread consumer/LockDataPtr relations and selected native text/source/constructed-owner chains; no managed request ownership, Event/media owner, pointer lifetime, successful lookup, backing-file open, decoding or audibility |
| `staticProviderPreparation.status=validated` | static reads and conditional descriptor transport; optional `providerStorageStatus=validated` adds conditional initialized dispatch and owned text storage; no live invocation, codec meaning, opened file, decoder generation or audibility |
| semantic category or coarse ownership | playback placement or runtime status |
| `actionTypeName` | execution, target scope, Event selection; `operation` stays the masked grouping key and the two SDK-unnamed words stay unnamed |

ModelView native route summaries distinguish full reviewed route audits from
`currentBuildCallsitesOnly` re-derivations. A successful current method/callsite
check cannot retain a prior build's stronger branch, endpoint or async statuses;
those remain `notReprovedOnSelectedBuild`. Authored definitions and possible
media links are independent of this native proof depth.

## Focused refresh commands

```bat
python -m scripts.webui.audio.build_audio
python -m scripts.webui.audio.build_audio --skip-decode --refresh-hirc
python -m scripts.webui.audio.build_audio --semantics-only --language CN
```

Inspect `--help` for non-CN or targeted maintenance options. Focused audits
(`play_sound_action_corpus`, `native_play_sound_string`, `hirc_action_corpus`,
`hirc_named_reach`) are listed in [`../../scripts/README.md`](../../scripts/README.md).

## Highest-value remaining gaps

- The residual is not the `wwise/unknown` folder (a raw physical category whose
  media mostly carry a named Event) but the media whose only reaching Event is
  still `hashed-event:0x...`, plus External-Source-shaped ids no Event reaches.
  Quote those two, not the folder size.
- Events spelled `Play_au_*` outside the byte grammar are recovered only from
  supported decoded payload roots; other roots need a measured reader, not a
  prefix guess.
- Close more authored consumer-to-Event and Event-to-media ownership paths, and
  recover selector/parameter meaning without conflating control with playback.
- Keep unsupported codecs, missing chunks and unobserved runtime branches
  visible.
- The native callsite catalog (`contracts/audio_native.json`) was reviewed on a
  previous build. On another build its rows -- callsites, selector setters,
  music state groups, ModelView routes, music transition registrations -- are
  re-derived by name and published only when every claim holds, with that
  build's addresses; the rest are withheld with a reason, and playback call
  chains stay withheld (`native_callsite_rederivation.py` owns the rules). A
  re-derived row proves the literal and playback path, not its reviewed trigger
  prose (`branchConditionStatus`). Authored and HIRC evidence is unaffected.

See [`../game_data_recovery.md`](../game_data_recovery.md) for durable
serialized-data and native-consumer conclusions, and
[`../game_data/audio_overview.md`](../game_data/audio_overview.md) plus the HIRC
files beside it for the Wwise chain.
