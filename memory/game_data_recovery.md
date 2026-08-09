# Game-data recovery

## Current status

Basic installed-data access is solved. The exporter indexes both VFS roots,
finds all required chunks, dumps WebUI-relevant blocks, and exports more than a
million Unity objects without relying on a generic silent fallback.

The remaining work is semantic: proving binary layouts, joining records across
systems, and separating authored configuration from live runtime behavior.

Evidence layers:

1. structured tables and JSON;
2. family-specific MemoryPack, FlatBuffer, and MonoBehaviour decoders;
3. the SQLite source graph joining tables, assets, Story, audio, Lua, and
   selected IL2CPP evidence.

## Refresh

```bat
python scripts\verify_export_freshness.py
.\export.bat
.\export.bat --export-from-game
.\export.bat --export-from-game --with-assets
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Use `--export-from-game` only for an intentional installed-data refresh.

## Known data model

- Both StreamingAssets and Persistent VFS roots matter.
- MissionRuntime uses complete-Persistent-or-whole-Streaming selection; never
  mix roots per file.
- Structured tables are the strongest authored foreign-key source.
- MemoryPack and FlatBuffer layouts must be family-specific and fail closed.
- MonoBehaviour `$partial` output is useful evidence, not a clean decode.
- Source root plus PathID is the safe Unity identity; PathID alone is not
  globally unique.
- Static configuration does not prove runtime evaluator order, server state,
  physics, AI decisions, or final formulas.

Current semantic coverage includes Story and mission data, progression,
economy, factory, world placement, characters, weapons, abilities,
projectiles, combat relationships, audio, videos, materials, and selected
runtime consumers.

Projectile configuration is structurally recovered through exact managed-
reference boundary checks: template skills, lifetime, collision, target
filters, movement segments/modes, effects, sound hashes, and source identity
are preserved. Gameplay-tag entries have both path-plus-id and compact id-only
serialized forms. `ProjectileTemplateData.skillDataBundle` describes behavior
owned by the projectile template; it does not by itself prove which playable
skill spawns that projectile. Skill-page placement therefore stays explicitly
identifier/authored-reference inferred, and unmatched internal templates stay
unassigned. Absence of a projectile template is not evidence of an incomplete
skill: visually ranged behavior can be authored as direct `SkillData` actions,
effects, hitboxes, summons, or another runtime system. Non-zero projectile
sound values are direct Wwise HIRC event IDs;
exact event traversal can link them to decoded media candidates. A Wwise
switch/random container may select one or several candidates at runtime, so
the exported link is not a claim that every candidate always plays.

Current SkillData and BuffData blobs use MemoryPack member counts 47 and 30;
the source graph also accepts the previously observed 45 and 29 variants.
Exact length-prefixed `au_`, `bark_`, and `radio_` references can be followed
through nested buff references and Wwise HIRC to playable media. Exact
character skill ids prove ownership; authored child-skill and enemy-id-prefix
placement remains inferred, while explicit enemy born-buff links are direct.

## Audio binary and playback evidence

The audio container is now understood far enough to preserve source identity
without treating decoded files as the source of truth. An AKPK payload may be
wrapped in the encrypted `:)xD` PCK form; after the VFS XOR step its sectors
describe languages, banks, sounds, and externals. Bank entries contain Wwise
`BKHD`/`DIDX`/`DATA` records, where `DIDX` supplies the media id, byte offset,
and byte length. Sound and external sectors can also point directly to WEM
media. WEM decryption is keyed by the media id, and already-RIFF/RIFX payloads
are left unchanged.

The HIRC parser follows event objects through action/container references and
records candidate numeric media ids. This is strong event-to-media evidence,
but a switch, random, or sequence container can select among candidates at
runtime; an exported link does not claim that every candidate always plays.
The current full-bank probe confirms that Endfield uses sound, action, event,
random/sequence-container, switch-container, actor-mixer, layer, and music
object families in the HIRC graph. Action objects consistently expose their
target id at the current offset-2 layout, but their remaining bytes are still
version-sensitive action flags and parameters; they must not be treated as
playback timestamps.

The current binary also proves that audio is not one flat event namespace.
`AudioAdapter` separately exposes event posting, states, switches, RTPCs,
listeners, spatial objects, seek/stop, and bank lifetime. `AudioManager` owns
distinct music, cue, gameplay-state, listener, spatial-room/emitter, NPC,
factory, and responsive-voice processors. `AudioMusicSystem` selects music
state groups for exploration, combat/boss, missions, dialogs, cutscenes,
factory, loading, and standalone playback. These controls remain separate from
media and Event objects in generated labels.

Current IL2CPP managed string literals provide a second exact name source.
Lowercased Wwise FNV-1 joins recover previously missing `au_*`, `bark_*`, and
`radio_*` names only when their hash is a HIRC type-4 Event. A string literal
alone proves that managed code shipped the identifier, not that it played.
Numeric event-designated fields in `AudioFactory`, `AudioBattleBuildings`, and
`AudioLevel` are normalized from signed JSON integers to uint32 and joined by
exact HIRC object id. Their table row and field give useful authored meaning
even when no string name survives. Music states, switches, RTPC values,
voice/media ids, and generic audio integers must not be promoted as Events.

The debug-only WebUI Audio view is generated by `build_audio.py`, or can be
refreshed independently after the authoritative index is current:

```bat
python scripts\build_audio.py --skip-decode --language CN
python scripts\build_audio_semantics.py --language CN
```

It keeps the large media inventory lazy, preserves event/media/physical-file
identity, exposes exact authored contexts and current-binary runtime types, and
labels HIRC descendants as runtime-selection candidates.
The strongest current authored playback joins are SkillData/BuffData audio
references, Timeline/cutscene audio fields, and AudioDialog-to-lipsync
`pathStem` associations. We do not yet have a complete runtime receiver,
activation chronology, or proof of which branch was selected in a live game.
There is nevertheless exact authored timing for a useful subset: recovered
Timeline `AudioEventPlayable` assets carry the event key plus stop/fade/seek
behavior, and the generated video bindings carry each clip's start and
duration on its audio track. `AudioDialogCustomEventTable` adds preload and
pre/post-enter/exit event hooks, while dialog-tree output gives ordered lines
and decoded durations. Those are playback schedules or hooks, not proof that
the engine reached every branch during a particular session.
The source graph now joins these layers: for example, `cs_video_e5m2_3`
resolves to both its SFX and music event keys through
`timelineEvidence.audioEventKeys`, with the originating Unity playable/path
evidence retained. This is a strong authored cutscene-playback relation; it
does not turn the timeline into a runtime profiler trace.

Next audio-recovery work should replace byte-sliding descendant discovery with
version-150 typed Sound/container/music decoding, beginning with the validated
Sound media/source field, then recover switch/state/random/music branch rules.
Also retain exact PCK sector and embedded-bank provenance during extraction,
identify Timeline/native audio receivers and activation paths, and validate
chronology against a captured game session. Keep source WEM ids, authored
references, controls, and runtime-selected candidates separate in reports and
WebUI labels.

## Source graph

Primary database:

```text
reports/source_graph/endfield_source_graph.sqlite
```

Typical queries:

```bat
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
python tools\endfield_source_graph.py issues --limit 20
```

Graph edges retain their evidence source. Exact foreign keys, serialized PPtrs,
and typed native paths are stronger than normalized names or token similarity.

## Remaining gaps

- Server-side mission/property producers and activation policy.
- Runtime-selected variants, state machines, and evaluator chronology.
- Additional family-specific MemoryPack/FlatBuffer schemas.
- Broader exact world-streaming scene decoding.
- Complete combat formulas rather than authored inputs and references.
- Runtime projectile spawn/call-site ownership, evaluated blackboard values,
  remaining unnamed projectile enums, and Wwise container selection.
- More exact joins between gameplay identities and runtime assets.
- Per-system negative/certification reports that fail visibly when inputs
  change.

Changing counts belong in `reports/`; durable conclusions belong here.
