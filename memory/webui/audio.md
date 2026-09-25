# Audio page recovery

## Purpose

Audio is an evidence browser over decoded media, Wwise Events, authored
consumers, semantic controls, and bounded runtime observations. It also stores
user research notes without modifying generated evidence.

## Inputs and recovery flow

1. AnimeStudio reads AKPK/Wwise payloads from StreamingAssets with Persistent
   overlay/fallback and decodes lossless FLAC directly.
2. `scripts.webui.audio.build_audio` owns decode, Wwise bank indexing, event-to-media
   traversal, Story relinking, and Gameplay sound sidecars. Shared SFX/music is
   written once under `game/Audio/shared/`; language voice belongs under
   `game/Audio/<LANG>/`.
3. `scripts.webui.audio.build_audio_semantics` orchestrates semantic domains under
   `scripts/webui/audio/semantics/` and publishes the compact page index/shards.
4. Optional verified runtime-trace bundles add only their matching observed
   request relation.
5. `webui/overrides/audio_notes.json` stores searchable manual notes through
   the local server.

Primary outputs are `webui/data/lang/<LANG>/audio/{index,events,media}.json`,
semantic shards, scene backgrounds, and Gameplay audio sidecars.

## Evidence boundary

- Media identity, Wwise graph relation, authored consumer, runtime request,
  selected branch, and audibility are separate layers.
- Music Switch Event details expose the exact stored type-`0x0C` tree paths
  already carried by `musicNodeEvidence`, with group IDs/types, path keys,
  leaf IDs, raw weights/probabilities and same-bank ownership status. The
  searchable view pages its rows; a missing same-bank declaration remains a
  local join gap. A stored path does not prove live group values, the selected
  leaf, or audible output. The WebUI requires argument-only `pathKeys`; an
  older generated shard that still includes the root sentinel shows no tree
  rows until a focused HIRC refresh republishes the Audio details.
- Event traversal and authored control curves do not prove live values or DSP
  response. A prefab source does not prove a scene instance.
- Runtime bundles must pass source, build, language, and terminal validation;
  otherwise they remain degraded and create no binding.
- Story-line binding can close purpose investigation for a media record, but
  does not prove that playback occurred in a captured session.
- Manual notes are user annotations and never upgrade confidence.
- An exact decoded `soundEvent` member is a naming candidate, including when it
  carries prose or outer whitespace. The page gains an Event name from this
  source only on a selected HIRC Event-object hash match; other authored
  references can remain visible with `foundInWwise=false`. The source index's
  `eventNameSources` still records raw decoded-member candidates for cache
  provenance; use `decodedPayloadEventNameRecovery.promotedNames` or the final
  `eventNames` to decide whether that source supplied an Event identity.
- Whole-record SkillData/BuffData PlaySound actions are retained in the
  Gameplay sound sidecar with raw literals, exact action paths, enclosing
  frame or event slots, native enum labels, and typed target settings. Only
  actions with a selected HIRC Event-object hash join Audio Event contexts;
  actions lacking that identity remain in the raw catalog. Authored config
  ownership and runtime execution remain distinct, so an unlinked Buff action
  can still show its trigger slot without acquiring a character or enemy.

### What each rendered state refuses to claim

The frontend renders these status tokens verbatim (they are listed in
[`../../webui/README.md`](../../webui/README.md)); this is what each one is
allowed to mean:

- an authored `monoBehaviourAudioIdField` role is a serialized field
  projection. No field is executed, posted, selected, or audible.
- Spawner pre-warning Event contexts carry the authored rotation only when the
  16-byte nullable Vector3 has its presence flag set. The three displayed
  values are stored components; no in-game effect placement or playback is
  observed from them.
- a prefab source row is not a recovered level instance.
  `sceneId`/`sourceName`/`sourcePath` appear only on an exact scene containment
  row, and disagreeing component and prefab-path identity fail closed with
  `conflictingPrefabInstanceIdentityJoins` rather than one route being chosen.
- a grammar-hash-preimage name is a weaker source than a shipped literal. It
  supplies only the owner and category its spelling encodes, and no caller,
  trigger, execution, branch, or audibility.
- an Event named from an authored serialized payload literal
  (`LevelScriptData`, `LevelScriptTemplateData`, `SpawnerConfig`, `Interactive`,
  `LevelData`) is an exact shipped-string match on the FNV-1 hash, so the
  spelling is proven. The payload root is provenance for the spelling only:
  which serialized field holds the literal is unidentified, so it is **not** a
  consumer, trigger or playback-location claim for that payload record.
- `noExplicitOutputBusSerialized` is an absence of serialized output-bus nodes.
  It implies no default or parent routing, no silence, and no effect-free path.
- `ownerKind=npc` requires the agreeing table pair plus an exact channel key. A
  mixed Event keeps the NPC on occurrence/Clip evidence only and receives no
  single NPC owner.
- namespace and native-response groups are identity-only. Shared media lists
  every named owner, while generic templates, live speaker choice, Wwise
  selection, and concrete playback locations stay unresolved.
- the AudioCue AST shows structure only: no condition truth, runtime variable
  value, handler dispatch, cue execution, branch selection, or audibility.
- `controlCatalog.staticRtpcAlignment` is authored static evidence. A missing,
  mismatched, malformed, or stale gate withholds the static names instead of
  showing stale identities, and `0x1802`/`0x1804` are never renamed.
- serialized effect-chain, RTPC, State, Aux-send, and ducking rows are possible
  routes. Runtime DSP order, effective inheritance, live control values, branch
  selection, and audibility remain unresolved.
- Built-in effect parameter names and authored base values appear only for
  reviewed classes after the selected native triplet and method bodies validate
  against the tracked Wwise contract. `effectParameterNativeGate` records that
  gate. An opaque row still exposes its raw class ID, byte length/SHA and exact
  plug-in media prefix; the Convolution Reverb and Mastering Suite parameter
  blocks currently remain in that state. RoomVerb's extra private floats show
  values and serialized offsets, with no selected-client use-role label.
  The HIRC inventory displays the generated gate status and the number of
  reviewed plug-in classes beside the exact/partial/opaque definition counts.
  A missing or malformed gate is shown as unverified, and none of these counts
  imply live effect activation or DSP output.
- a recovered semantic category or coarse ownership never upgrades playback
  placement or runtime status.
- an action row's `actionTypeName` is the Wwise SDK identifier for the whole
  serialized 16-bit action type, taken from the pinned
  `wwise_sdk_enums` contract through
  `scripts/webui/audio/semantics/wwise_enums.py`. `operation` remains the masked
  high byte and stays the grouping key, because that is what decides the body
  layout. A name is a serialized constant's spelling: it establishes no
  execution, no target scope, no event selection, and no audibility, and the two
  words the SDK does not name are shown unnamed rather than fitted from the
  suffix pattern. See
  [`../game_data/audio_overview.md`](../game_data/audio_overview.md).

## Focused refresh

```bat
python -m scripts.webui.audio.build_audio
python -m scripts.webui.audio.build_audio --skip-decode --refresh-hirc
python -m scripts.webui.audio.build_audio_semantics --language CN
```

Inspect `--help` for non-CN or targeted maintenance options. Do not duplicate
audio logic in the semantic publisher or import either entry point as a helper.

## Remaining gaps

- Media under `wwise/unknown` are not unnamed media: `unknown` is the raw
  physical category, and most such rows already carry an exact named Event.
  The real residual is the media whose only reaching Event is still
  `hashed-event:0x...`, plus the External-Source-shaped ids no Event reaches at
  all. Quote those two, not the folder size.
- Wwise Events named `Play_au_*` are outside the harvested
  `au_`/`bark_`/`radio_` grammar. The exact decoded-member source recovers
  those present in its supported payload roots after a selected HIRC hash
  match; other payload roots still need a measured reader rather than a prefix
  guess.
- Close more authored consumer-to-Event and Event-to-media ownership paths.
- Recover selector/parameter meaning without conflating control with playback.
- Keep unsupported codecs, missing chunks, and unobserved runtime branches visible.
- The native audio catalog was reviewed on the previous build
  (`contracts/audio_native.json`). On another installed build the callsite
  catalogs -- managed-literal and selector callsites, SwitchAudioCustomState
  callsites and voice-response triggers -- and the AnimatorMono, enemy
  voice-action and AI-bark routes, the Wwise music state groups (setter,
  enum members from the installed metadata, and each callsite that still
  loads its value and calls the setter) and the native selector setters are
  re-derived by name
  (`scripts/webui/audio/semantics/native_callsite_rederivation.py`): a row is
  published only when its consumer resolves, its literal reaches the consumer
  (in the body, a reached helper, or the selector field's initializer) and the
  playback sink is reached, with that build's addresses; the rest are withheld
  with a reason. A re-derived row proves the literal and playback path, not
  its reviewed trigger prose (`branchConditionStatus`). The ModelView routes
  re-derive the same way: the consumer must still call each target, where a
  target that changed owner (the handler registry moved into
  `ModelAnimatorContext`) is a reviewed re-reading. Music transition
  registrations are read from each `RegisterTransitionAction` call's own
  arguments (state mask, enter/leave, action order, delegate target): on the
  current build every state registers an `_OnEnter*` (order 5) / `_OnLeave*`
  (order 1) pair, and none matches the reviewed pairing, which the previous
  build can no longer confirm. Playback call chains stay withheld: their links
  include delegate callbacks and native engine stages a call-graph check cannot
  prove, and sibling entry points are listed as sequential stages. The selector catalog used to publish the music setters and
  selector callsites with no build gate at all; with no measured build they
  now carry no native field.
  Authored and HIRC evidence is unaffected.

See [`../game_data_recovery.md`](../game_data_recovery.md) for durable
serialized-data and native-consumer conclusions, and
[`../game_data/audio_overview.md`](../game_data/audio_overview.md) plus the
HIRC files beside it for the Wwise chain.
