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

The current banks are Wwise bank version 150. Event traversal now uses only
typed downward edges: Event action arrays; Action `U16 actionType` plus target
at offset 2; reciprocal-parent-proven Children arrays for object types 5/6/7/9;
and the Sound `AkBankSourceData` media id at offset 5. Play (`0x0400`) and
PlayEvent (`0x2100`) are traversed, while Stop (`0x0100`) and other control
actions are recorded but not followed. This replaced the former byte-sliding
u32 scan, which could climb Sound parents or follow incidental property,
playlist, and switch-map integers into sibling graphs.

The output calls decoded Sound leaves *possible media*, not equivalent options
or a playback trace. Each leaf retains its Play roots and Random, Sequence,
Switch/State, Layer, or direct-Sound relation. Multiple Play roots are separate
logical playback branches, while children below selector containers are
runtime alternatives; action delay/timing properties are not decoded far
enough to claim simultaneity. Distinct media ids remain distinct authored
leaves, while SHA-256 content equivalence identifies byte-identical decoded
files. A partial typed graph fails closed and is visibly marked partial rather
than implying silence. Music object types 10-13 remain unsupported typed
topologies and likewise fail closed.

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
groups possible media by semantic context, Play root, selector relation,
traversal completeness, and decoded-content equivalence.
The strongest current authored playback joins are SkillData/BuffData audio
references, Timeline/cutscene audio fields, and AudioDialog-to-lipsync
`pathStem` associations. We do not yet have a complete runtime receiver,
activation chronology, or proof of which branch was selected in a live game.
Playable skill linkage is recorded per Event instead of inheriting a whole
group's confidence. An exact Gameplay action id joined to the same SkillData
file proves an authored dependency; a complete length-prefixed Event reference
in that file is `skillDataEventReference`, while an exact
SkillData-to-BuffData reference walk is `skillBuffChain`. This generic scan
does not recover the containing field or callsite. Child-skill family-prefix
placement remains inferred. Dependency-only paths retain
`conditionAndTimingUnresolved`; only the decoded action families below prove a
request operation and authored timing.

The current BuffData MemoryPack union identifies `PlaySoundActionData` at tag
`0x010d` with 22 serialized members (the common action prefix plus 18 sound
fields). Fifteen authored occurrences across 12 Events now decode through an
exact action boundary. They preserve start/end frames, enabled/priority data,
interrupt and initial-seek milliseconds, stop-on-end/fade lifetime, temporary
emitter and target/mount/weapon routing, and time-dilation pause/seek controls.
IL2CPP metadata independently validates the 18 fields and the runtime
`PlaySoundAction` lifecycle that stores playing ids, posts on an object or at a
position, seeks, ticks, and stops retained instances on end. All 12 exact Event
names hash to current Wwise Event objects and resolve to decoded media. The
remaining `TargetSettings` payload is only byte-bounded, authored frames are
not converted to wall-clock time, and the runtime activation condition remains
unresolved. The Gameplay page therefore
places only exact skill-config Event references back on their skill rows, leaves
inferred links in the final audio section, and never duplicates one Event
between those placements. The Audio view exposes exact/inferred trigger
filters, a separate authored-PlaySound-action filter, and the recovered action
lifetime/routing evidence. Ownerless PlaySound actions remain canonical Audio
contexts rather than being guessed onto a skill.

Interactive audio now has both of its serialized request layers. The global
`InteractiveAudioSetting` maps 285 model/sub-template state occurrences to 105
Events. Per-entity `InteractiveData` uses current BaseComponentData union tag
`0x005d`; a focused exact signature plus the existing typed body parser recovers
261 non-empty occurrences across 96 components and 190 Events (one authored
empty Event string remains a visible source defect, not an Event). The layers
overlap on only 25 names and together identify 270 Events: 264 are current
Wwise Event objects and 249 reach 948 decoded possible leaves. Runtime metadata
proves the 20 `EAudioTriggerState` values and the component methods that switch,
enter, exit, process, and post state/custom-state audio. This proves the
lifecycle-state-to-Event request mapping, not that a particular entity entered
the state in a captured session. `AudioGlobalConfig` adds 486 exact global
init, entity-init, audio-state-transition, and music/lifecycle Event contexts;
state masks are high-level engine lifecycle conditions, not Wwise SetState
operations.

Projectile audio preserves seven exact uint32 Wwise Event slots per decoded
projectile: launch, loop, reach, hit, block, finish, and proximity sizzle. The
current 265 nonzero field occurrences cover 123 Events; 96 previously
context-free playable Events now gain 343 possible leaves. Projectile identity,
source PathID, field/phase, and exact template SkillData references are retained,
but the skill reference proves projectile configuration only. Runtime spawn,
lifecycle execution, and Wwise branch selection remain unobserved.

`AudioCueTable` is an expression system rather than a flat Event list. The
current 175 cue definitions contain 291 handlers: only 325 `behaviourExpr`
nodes with `exprType=3` are exact downstream Event requests (229 unique Event
names). The 42 `exprType=8` strings are runtime cue-variable operands and stay
in a control catalog. `AudioGlobalConfig` has 17 lifecycle music-cue IDs; 15
resolve through the table to 153 Event-request occurrences, while the two
factory-area cue definitions remain explicitly missing. Its eight serialized
RTPC names and seven additional managed-code RTPC literals are parameters, not
Wwise Events.
Gameplay audio also consumes recovered Unity `AnimationClip.m_Events` rows for
the exact `PostAudioEvent`, `PostAudioEventAdvance`,
`PostAudioEventAtPosition`, and `OnCustomFootStep` callbacks. The callback
time, function, payload, clip PathID, and AssetMap container are exact authored
evidence. Playable-character and enemy-template ownership is inferred only
when the clip name contains the unique table-id suffix token; the callback
does not prove that a current controller can reach the clip or which Wwise
container branch wins at runtime. Canonical Wwise events therefore retain
per-clip owner contexts rather than one global owner.

Playable-character callback ownership must not be extended to every leaf of a
shared Event. The apparent 10,000-plus per-character totals were sums of
Event-to-possible-media associations: 375 animation Events are used by multiple
playable characters, and generic `player_fol_*` footstep/cloth selectors account
for most of the expansion. For example, `player_fol_fs_walk` is used by 26
characters and has 2,326 typed possible leaves behind three Play roots, 38
Switch containers, two Layers, and 817 Random containers. The shipped
`FootStepHandler` separately updates material and water switches, so those
leaves are a global runtime selector surface, not character-owned files. The
Gameplay UI separates single-owner callbacks from shared animation systems;
the Audio view tags shared playable-animation and footstep/material Events.
Animation Event identity is lowercased for the Wwise join while every authored
spelling is retained as evidence, preventing case-only callbacks from
duplicating candidate associations. The compact Gameplay sidecar retains bank
definition and root Stop counts plus per-selector node and child-edge totals,
so a large possible-leaf count remains auditable without loading raw HIRC data.

Two additional Gameplay joins fill gaps outside SkillData/BuffData. Exact
SkillData strings embedded in recovered `EnemyData.AbilitySystemData` allow
enemy variants to reuse their authored template skill bundle, with the
template-to-variant relation kept as inferred ownership. In contrast,
`CharacterTable.profileVoice` is direct character ownership: its combat,
attack, skill, hurt, and death voice ids join one-to-one to `AudioDialog`
media, with optional `AIBark` trigger-prefix semantics. Animation catalogs and
their detailed callback evidence are separate lazy sidecars so opening the
Gameplay view does not eagerly fetch every clip context.

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

Next audio-recovery work should decode v150 switch-value mappings, Action
delay/property bundles, and music types 10-13, then connect current music-table
state/control rows to MusicTrack source media. Also fingerprint PCK inputs for
cache invalidation, identify Timeline/native audio receivers and activation
paths, finish PlaySound `TargetSettings` and action-condition semantics, recover
the other ability/AI/interactive audio-trigger action families, and validate
chronology against a captured game session. Gameplay
follow-up should finish the partial `EnemyData.AbilitySystemData` mode-tail
decoder, connect animation clips through controllers instead of filename
ownership alone, recover per-callback material/water/switch values where the
binary permits it, and recover native effect-audio components for the remaining
silent templates. Keep source WEM ids, authored references, control/state
objects, possible media leaves, and observed live playback separate in reports
and WebUI labels.

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
