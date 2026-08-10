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
exact event traversal can link them to decoded possible media leaves. Wwise
Play roots and switch/random/layer containers can represent different logical
branches, so the exported set is not a claim that every file always plays or
that every file is one equivalent option.

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
than implying silence. Wwise v150 MusicSegment, MusicTrack, MusicSwitch, and
MusicRandomSequence objects now use bounded type-specific layouts: all 5,405
current music objects expose an exact parent, and all 3,380 parent-node child
structures parse through reciprocal non-empty lists or a unique typed empty
tail. The `au_music_main`, `au_music_meta`, and `au_music_login` roots reach
1,175 unique decoded media ids with complete traversal. This recovers the
authored music graph and possible leaves; live music state, cue conditions,
switch values, playlist position, and the selected track remain unobserved.

Version-150 playback Actions now expose their exact scalar and ranged property
bundles plus the Play/PlayEvent tail. In the current banks all 20,322 Play and
361 PlayEvent bodies consume exactly; authored fields include 180 DelayTime,
1,065 TransitionTime, and 47 Probability occurrences across those operations.
For Gameplay, 568 Events dispatch multiple playback Actions: 550 have no
serialized delay on any Action and 18 have explicit differing delay state or
value. The UI therefore calls the former `coDispatchNoExplicitDelay`, never
proven simultaneous; probability remains an unevaluated Action gate, Action
ordinal is membership rather than sequence order, and absent delay is not
synthesized as explicit zero.

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

The WebUI Audio view is generated by `build_audio.py`, or can be
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
lifetime/routing evidence. Fourteen of the 15 actions now reach gameplay owners
through exact authored Buff dependencies; the remaining
`buff_chr_0030_zhuangfy_combo_skill_target_mark` action has no current
SkillData/born-buff chain and remains an explicit owner gap rather than being
guessed onto a skill.

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

Interactive physics audio is now an exact authored layer rather than a string
scan. Current `PhysicsAudioComponentData` is BaseComponentData union tag
`0x00be`, member count 1, containing one complete 21-entry dynamic-property
map. The sole current definition, `int_kickable_ball`, supplies six non-empty
movement/hit/rotation Event requests plus the
`rtpc_int_kickable_ball_speed` velocity-squared RTPC; its other two RTPC fields
and general rotation-loop Event are authored empty strings. `InteractiveTable`
proves that `int_kickable_ball` and alias `int_tumble_weed` consume the same
definition, so Audio keeps one definition with two consumers. Source SHA-256,
component/property offsets, authored keys (including the two shipped spelling
mismatches), and runtime-field mappings remain visible. This proves serialized
configuration and native `ApplyProperties` assignment shape, not component
instantiation, physics thresholds being crossed, RTPC updates, Event posting,
or Wwise branch playback.

`ModelViewStateControllerData` now has a complete fail-closed current-corpus
decoder rather than a byte scan. All 486 mirrored controllers consume exactly;
their state graphs contain 918 Event behaviors (union tag `0x0001`, mc14), 67
positioned Event behaviors (`0x0002`, mc14), nine RTPC behaviors (`0x0003`,
mc13), and 89 spatial/portal controls (`0x0004`, mc12). Normal nonzero int32
AudioIds yield 954 exact contexts across 467 hashes with the full
model/layer/state/behavior chain. Thirteen custom-branch `customAudioId` strings
remain unresolved controls and are never promoted to Events. Exact serialized
controller-id matches associate 321 audio-bearing controllers with 127
InteractiveData templates and 522 interactive identities, but the containing
property slot is unresolved, so this is an authored association rather than
runtime ownership. The four runtime families retain current Deserialize and
Execute method/token/VA anchors; state entry, behavior execution, Event posting,
RTPC/spatial application, and Wwise branch playback remain unobserved.

Projectile audio preserves seven exact uint32 Wwise Event slots per decoded
projectile: launch, loop, reach, hit, block, finish, and proximity sizzle. The
current 265 nonzero field occurrences cover 123 Events; 96 previously
context-free playable Events now gain 343 possible leaves. Projectile identity,
source PathID, field/phase, and exact template SkillData references are retained,
but the skill reference proves projectile configuration only. Runtime spawn,
lifecycle execution, and Wwise branch selection remain unobserved.

Spawner enemy pre-warning audio now uses the exact current
`SpawnerEnemyLibraryItem` mc13 prefix rather than the previous mc11 layout.
All 560 current StreamingAssets configs decode without failure: 1,407 enemy
rows contain 1,204 non-empty `preWarnAudioEventKey` occurrences across 19
authored names. The Audio view retains the row-local enemy/template, timing,
effect, source offset/path, and source SHA-256 even for the 18 names absent from
the current CN HIRC Event inventory; one name resolves to a current Event.
This proves authored spawn-warning requests, not that a spawner executed.
Every current `bornBehaviorData` value is null, so a future non-null member-18
payload fails closed until an authored fixture proves its serialized layout.

NPC patrol-point audio now uses one fail-closed current MemoryPack cursor from
`LevelData/43` member 31 through `NpcPatrolData/9`, point/3, and the complete
`PatrolSubAction/26` variable prefix and typed sub-action union. Across 958
Persistent LevelData files, 147 non-empty frames decode without failure (701
patrols, 5,160 points, and 1,520 actions); 34 tag-1
`PatrolSubPlayAudioData/1` actions reference the single Event hash `0x0b1279e0`,
which is absent from the current CN HIRC Event inventory. Patrol, point, action,
offset, and source identity are exact authored context; reaching the point,
executing the action, and posting or selecting Wwise media remain unobserved.

Character-interaction perform audio now has a separate fail-closed current-
build decoder. The 181 StreamingAssets configs and identical Persistent mirrors
contain five `AudioEventActData` records (action-union tag `0x02`, mc15) in four
fully bounded mc27 owners: one exact `endActions` placement and four
`startActions` placements. Their four numeric `AudioId` values currently match
no CN HIRC Event, so Audio retains hash-only contexts with config id, action
phase/index, timing, logic id, attached-actor controls, offsets, and source
SHA-256. This proves authored perform-config requests only; perform execution,
runtime actor resolution, AudioId registration, Event posting, and Wwise branch
playback remain unobserved.

Seventeen current LevelScript audio ActionBase layouts now decode from their
exact union tag/member count and generated-setter field order. The overlaid
corpus has 1,842/1,842 decoded records: 1,394 constant Event requests, 290 named
AudioCue invocations, 22 dynamic Event parameters, and 152 exact music/state/
variable/stop/bark controls with 23 dynamic control bindings. Constant Events
receive exact script/action/role/routing contexts in Audio. Cue names, dynamic
parameters, playback handles, placeholder-music ids, and state/variable writes
remain typed control records when their runtime value is unresolved; no name or
live value is synthesized for them. Native `AudioCueSystem.PostCue(string)`
hashes the exact managed string with `AudioHashGenerator.Compute`, then looks up
the resulting uint32 in `AudioCueHandlerIndex`. The hash is FNV-1 over UTF-16
code units with ASCII-only `A-Z` folding and no whitespace trim. Normalizing the
signed `AudioCueTable` keys to uint32 resolves 207/290 invocations and 103/170
distinct authored names without collisions; 83 invocations remain explicitly
missing from the current table. Exact matched `behaviourExpr` type-3 rows add
222 LevelScript cue-to-Event contexts across 103 Events. Script execution,
current-level handler selection, condition evaluation, and Wwise playback stay
unobserved. The shipped `SetAudioGlobalParameter` type is not decoded because
no current serialized row proves its field shape.

`AudioCueTable` is an expression system rather than a flat Event list. The
current 175 cue definitions contain 291 handlers: only 325 `behaviourExpr`
nodes with `exprType=3` are exact downstream Event requests (229 unique Event
names). The 42 `exprType=8` strings are runtime cue-variable operands and stay
in a control catalog. `AudioGlobalConfig` has 17 lifecycle music-cue IDs; 15
resolve through the table to 153 Event-request occurrences, while the two
factory-area cue definitions remain explicitly missing. Its eight serialized
RTPC names and seven additional managed-code RTPC literals are parameters, not
Wwise Events.

Two shipped LevelEvent audio inputs are now typed separately from playback.
`OnAudioStateChanged` (union `0x0048`, event key 148) compares masked previous
and current `EAudioState` values; `OnMusicBeatEvent` (`0x007a`, event key 44)
tests an authored `AudioCallbackType` flag mask against a runtime music callback.
An exhaustive Persistent-over-Streaming scan of the current 4,517 LevelScripts
found zero authored instances, so the Audio control catalog reports both
definitions with occurrence count zero and creates no Event or media rows.

LevelScript radio playback is now decoded as a separate authored-media relation.
Six exact ActionBase layouts (`PlayRadio`, `PlayRadioAndWait`, `Play3DRadio`,
`Play3DRadioAndWait`, `StopRadio`, and `ToggleClearScreenButRadio`) decode all
2,526 current records: 2,177 constant radio-id bindings and one dynamic binding
remain explicit. RadioTable contributes 2,909 definitions and 4,940 ordered
lines; 3,078 referenced lines join 3,073 lazy media contexts through exact
`audioDialogPath` stems (2,681 referenced lines decode, 397 remain unresolved).
`radioId` and `audioOverride` are dialog identities, not Wwise Events; action
execution, line selection, playback, and dynamic ids remain unobserved. The
Audio page exposes routing, actor, line order, lifecycle, unresolved rows, and
truncation counts while retaining direct-dialog media and lazy players.

Two LevelScript dynamic bindings remain deliberately unresolved. The exact
`LST_SlugCoward_Graph` property map names `catchAudio` with the default
`au_npc_obj_slug_02_g01_get`; its `PlayAudiAtPosition` action uses
`paramSource=100`, but current instances do not serialize a template path, so
Audio labels them template-default candidates rather than direct ownership.
`LST_Race_Graph` similarly declares empty `Start_music`, `Exit_music`,
`Win_music`, and `Lose_music` properties behind twenty `paramSource=200`
`PlayAudio` bindings. Separate constant `au_gameplay_race_*` actions are not
merged into those placeholders. The 100/200 source values remain unnamed
serialized binding sources until a native mapping or populated instance is
recovered.

Gameplay audio also consumes recovered Unity `AnimationClip.m_Events` rows for
the exact `PostAudioEvent`, `PostAudioEventAdvance`,
`PostAudioEventAtPosition`, and `OnCustomFootStep` callbacks. The callback
time, function, payload, clip PathID, and AssetMap container are exact authored
evidence. Playable-character and enemy-template ownership is inferred only
when the clip name contains the unique table-id suffix token; the callback
does not prove that a current controller can reach the clip or which Wwise
container branch wins at runtime. Canonical Wwise events therefore retain
per-clip owner contexts rather than one global owner.

`OnCustomFootStep` parameters now retain their exact stock-client meaning:
`intParameter` masks select Left/Right foot (`0x03`), None/Step/Jump/Land VFX
(`0x1c`), and max-weight/compose-max/custom-weight/force-play filtering
(`0xe0`). Only CustomWeight uses `floatParameter` as its playback threshold;
all 13,303 current callbacks use IsMaxWeight or ForcePlay, so their 11,443
authored `0.5` and 1,860 authored `0.0` floats are inactive for playback.
VFX has a separate exact runtime clip-weight threshold of `0.5`. The current
4,213-clip corpus covers 35 authored spellings (32 canonical Events), with
6,831 character, 67 enemy, and 6,405 owner-unresolved occurrences. Native
`FootStepHandler` evidence proves left/right ground queries, material/custom-tag
AudioId posting, and water-depth RTPC updates; it does not map a material or
water value to a Wwise switch child, prove which callback receiver executed,
or provide a live playback trace.

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

Next audio-recovery work should finish live-value/state capture for the now
typed v150 switch-value mappings, Action delay/property bundles, and music
types 10-13, then connect current music-table
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
