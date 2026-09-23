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
- Event traversal and authored control curves do not prove live values or DSP
  response. A prefab source does not prove a scene instance.
- Runtime bundles must pass source, build, language, and terminal validation;
  otherwise they remain degraded and create no binding.
- Story-line binding can close purpose investigation for a media record, but
  does not prove that playback occurred in a captured session.
- Manual notes are user annotations and never upgrade confidence.

### What each rendered state refuses to claim

The frontend renders these status tokens verbatim (they are listed in
[`../../webui/README.md`](../../webui/README.md)); this is what each one is
allowed to mean:

- an authored `monoBehaviourAudioIdField` role is a serialized field
  projection. No field is executed, posted, selected, or audible.
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
- a recovered semantic category or coarse ownership never upgrades playback
  placement or runtime status.

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
  `au_`/`bark_`/`radio_` grammar, so a shipped payload literal spelling one of
  them is currently dropped. Widening the grammar is a separate, measurable
  step, not a prefix guess.
- Close more authored consumer-to-Event and Event-to-media ownership paths.
- Recover selector/parameter meaning without conflating control with playback.
- Keep unsupported codecs, missing chunks, and unobserved runtime branches visible.
- Native consumer routes (ModelView, voice triggers, managed-literal and
  selector callsites) are withheld on the installed build: their catalog is
  pinned to the previous build (`contracts/audio_native.json`) until it is
  re-derived by name. Authored and HIRC evidence is unaffected.

See [`../game_data_recovery.md`](../game_data_recovery.md) for durable
serialized-data and native-consumer conclusions, and
[`../game_data/audio_overview.md`](../game_data/audio_overview.md) plus the
HIRC files beside it for the Wwise chain.
