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
4. Optional verified runtime-trace bundles add only their matching observed
   request relation.
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

## Evidence boundary

- Media identity, Wwise graph relation, authored consumer, runtime request,
  selected branch and audibility are separate layers
  ([`../game_data/audio_overview.md`](../game_data/audio_overview.md)).
- Event traversal and authored control curves do not prove live values or DSP
  response. A prefab source does not prove a scene instance.
- Runtime bundles must pass source, build, language and terminal validation;
  otherwise they stay degraded and create no binding.
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

### What each rendered state refuses to claim

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
| built-in effect parameter names (`effectParameterNativeGate`) | shown only after the selected native triplet validates; Convolution Reverb and Mastering Suite show their verified class identity and native read span while settings stay opaque (byte length/SHA, plug-in media prefix); RoomVerb's private floats have no use-role label; a missing gate shows unverified; no live activation |
| semantic category or coarse ownership | playback placement or runtime status |
| `actionTypeName` | execution, target scope, Event selection; `operation` stays the masked grouping key and the two SDK-unnamed words stay unnamed |

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
