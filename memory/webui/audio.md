# Audio page recovery

## Purpose

Audio is an evidence browser over decoded media, Wwise Events, authored
consumers, semantic controls, and bounded runtime observations. It also stores
user research notes without modifying generated evidence.

## Inputs and recovery flow

1. AnimeStudio reads AKPK/Wwise payloads from StreamingAssets with Persistent
   overlay/fallback and decodes lossless FLAC directly.
2. `scripts.build_audio` owns decode, Wwise bank indexing, event-to-media
   traversal, Story relinking, and Gameplay sound sidecars. Shared SFX/music is
   written once under `structured/Audio/shared/`; language voice belongs under
   `structured/Audio/<LANG>/`.
3. `scripts.build_audio_semantics` orchestrates semantic domains under
   `scripts/audio_semantics/` and publishes the compact page index/shards.
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

## Focused refresh

```bat
python scripts\build_audio.py
python scripts\build_audio.py --skip-decode --refresh-hirc
python scripts\build_audio_semantics.py --language CN
```

Inspect `--help` for non-CN or targeted maintenance options. Do not duplicate
audio logic in the semantic publisher or import either entry point as a helper.

## Remaining gaps

- Close more authored consumer-to-Event and Event-to-media ownership paths.
- Recover selector/parameter meaning without conflating control with playback.
- Keep unsupported codecs, missing chunks, and unobserved runtime branches visible.

See [`../game_data_recovery.md`](../game_data_recovery.md) for durable Wwise,
serialized-data, and native-consumer conclusions.
