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
.\export.bat --from-game
.\export.bat --from-game --with-assets
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Use `--from-game` only for an intentional installed-data refresh.

## Known data model

- Both StreamingAssets and Persistent VFS roots matter.
- MissionRuntime uses complete-Persistent-or-whole-Streaming selection; never
  mix roots per file.
- Structured tables are the strongest authored foreign-key source.
- MemoryPack and FlatBuffer layouts must be family-specific and fail closed.
- MonoBehaviour `$partial` output is useful evidence, not a clean decode.
- Source root plus PathID is the safe Unity identity; PathID alone is not
  globally unique.
- Static configuration alone does not prove runtime evaluator order, server
  state, physics, AI decisions, or final formulas. Native IL2CPP paths can
  establish the shipped stock-client formula, but active IFix patches and
  server corrections remain a separate evidence boundary.

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
The legacy local `build_data_index.py` now gates the current 47/30 layouts,
reports a visible unsupported-member-count result on future drift, consumes
BuffData `onlyUseSelfTimeDilation` and SkillData `useAIExclusiveFrame` at their
exact tail positions, and records SkillData `aiExclusiveFrame` in the recovered
schema. Its `webui/data/game_data/` output remains a broad diagnostic preview,
not an active semantic page or runtime-formula source.
Every current BuffData and SkillData row in the merged Persistent plus
StreamingAssets diagnostic corpus now reaches an exact post-id tail boundary.
This is boundary proof, not a claim that every nested action is semantically
decoded.

Non-empty Buff stack effects have exact versioned skips for the observed
EffectAction layouts. The current member-17 form contains an EffectActionCfg
member-85 payload, moves the effect-name length to `+71`, ends at `581 +
effectNameBytes`, and adds the guard-source target-settings/bool tail. The
parser also distinguishes the serialized empty stacking-key prefix from a
non-empty stacking key; it no longer calls that prefix a terminal pad. Current
stack-effect rows have empty `effectPosData`, which is validated explicitly;
the inner EffectActionCfg field semantics remain partial and fail closed if
that list becomes non-empty.

The four energy-shard Buffs use a second validated IgniteEventAction nested-
block header version; their four block boundaries, header versions, and tail
codes are exact while the inner action data remains opaque. Gameplay tags also
have compact forms in this corpus: Buff `tagsAfterTriggerExtendBuffAction` can
be a packed u32-id list, and Skill member-1 tag records contain only the tag id.
Recognizing the latter resolves the formerly ambiguous Ikut normal-skill id
anchor and preserves subsequent toggle/UI-range fields at their real offsets.
Some Skill smart-target and SwitchToBuffConfig inner payloads remain preserved
as bounded diagnostics even though their final tail handoff is exact.

Focused validation:

```bat
python -m unittest scripts.tests.test_build_data_index_combat_memorypack -v
python scripts\build_data_index.py
```

Exact length-prefixed `au_`, `bark_`, and `radio_` references can be followed
through nested buff references and Wwise HIRC to playable media. Exact
character skill ids prove ownership; authored child-skill and enemy-id-prefix
placement remains inferred, while explicit enemy born-buff links are direct.

## Enemy level stats and variants

Enemy HP, ATK, DEF, and other level-dependent values come from exact rows in
`EnemyAttributeTemplateTable.levelDependentAttributes`. The level coordinate is
authored in each usable row; a row without that coordinate is omitted, and the
builder never derives a level from row position or interpolates between points.
Gameplay sliders therefore expose only the levels that have source rows. A
missing slider level means the export has no supported point, not that the
value is zero or follows a reconstructed curve.

Enemy variants do not universally have independent stat curves. Each
`EnemyTable` variant names an `attrTemplateId`: variants that name the same
attribute template share the same raw HP/ATK/DEF curve, while variants with
different attribute templates use their own exact rows. Even when the base
curve is shared, variant-specific `attrModifiers`, born buffs, AI/model fields,
and other combat configuration can differ, so shared displayed stats do not
prove identical live behavior. The Gameplay variant selector resolves the
selected variant's exact attribute template before showing its stats.

## Combat runtime and formula evidence

The installed `GameAssembly.dll` and IL2CPP metadata, joined to the shipped
`BattleConst.json`, SkillData, and BuffData, establish the stock-client combat
pipeline below. This is stronger than inference from field names, but it is not
a claim about a server correction or a replacement loaded through IFix.

For ordinary damage, `BattleFormula.CalculateDamage` has the multiplicative
shape:

```text
finalAttackValue
* weaknessDamageScalar
* criticalFactor
* defenseFactor
* (1 - shelterDamageScalar)
* max(0, elementalResistanceFactor)
* abnormalStatusFactor
* physicalInflictionFactor
```

Critical hits use a random roll against `CriticalRate`; a successful roll uses
`1 + CriticalDamageIncrease`. With the shipped
`BattleConst.efficiencyOfDEF = 0.01`, defense is piecewise:

```text
DEF >= 0: 1 / (1 + 0.01 * DEF)
DEF < 0:  2 - 0.99 ^ (-DEF)
```

The elemental factor for Physical, Fire, Pulse, Cryst, Natural, and Ether is
`(1 - typeResistance / 100) * typeDamageTakenScalar`. Real damage uses neutral
defense and elemental factors but still traverses the other ordinary
multipliers. LifeDrain is a distinct early-return path that uses
`finalAttackValue` and skips the ordinary critical, defense, resistance,
weakness, shelter, and status segment. Abnormal/burst/Burning/Shatter
decorators multiply `IgniteDamageScalar`; Crush, Airborne, KnockDown, and
Fracture multiply `PhysicalInflictionDamageScalar`. Guard reduction is authored
on DamageUnits and processors outside this universal scalar.

`finalAttackValue` starts with the authored DamageUnit attack calculation,
passes the modifier hook and configured damage-scale zones, then applies
`atkScale`. Attacker and defender zone values start at 1; an applicable zone
merges them by multiplication or `attacker + defender - 1`, clamps the zone to
zero or above, and the final zone scale is their product. Named contributions
include damage-type, ignite/burst, skill-type, broken-target, enhanced, and
vulnerable damage. Attacker ATK, defender DEF, penetration, critical,
DamageScale, instant-attribute, and final-result processors can modify the
inputs or result; many processor bodies dispatch through IFix, so their active
hotpatch arithmetic is not completely recoverable from the stock method body.

Skills are runtime action graphs, not one formula per localized description.
SkillData supplies cast/cooldown/duration frames, target selectors, movement,
buff links, blackboard data, and an ActionGroup containing timeline and passive
event actions. AbilityAction instances run create, execute, tick, end, and
recycle phases. A DamageAction owns one or more DamageUnits, each selecting its
damage type, HP/poise calculation, attack scale, processors, guard behavior,
effects, sound, and costs. Runtime Skill state additionally owns timers,
targets, cast context, interruption/cost state, blackboard values, and attached
buffs.

BuffData is likewise a composition rather than a hardcoded class per buff. It
can combine attribute, damage, heal, poise, and global modifiers; shields;
tags; lifetime and trigger rules; stacking/dispel policy; events; timeline
actions; child buffs; and blackboard values. Damage modifiers choose attacker
or defender ownership, conditions, processors, and timing hooks. Stacking modes
cover unlimited, priority, stack, enhance, refresh, extend, modify, unique, and
duration-overwrite combinations. Buff events distinguish start, trigger,
finish, enable/disable, enhance changes, dispel, and interruption. Shields
filter damage types and define value/count/priority and removal behavior before
the remaining damage reaches HP.

Attribute modifiers have Addition, Multiplier, FinalAddition,
FinalMultiplier, and corresponding Base lanes. The recovered final-stage order
is approximately
`((value + Addition) * max(0, Multiplier) + FinalAddition) * FinalMultiplier`;
base-stage conversions and clamps occur earlier. Normal healing uses
`baseHeal * (1 + healer.HealOutputIncrease + receiver.HealTakenIncrease)`
before heal modifiers. Poise damage uses calculated poise multiplied by the
attacker output and defender taken scalars before poise modifiers.

The unresolved live boundary is material: `CalculateDamage` checks IFix, many
processors are patch-dispatched, and server-only validation is absent from the
client. Static recovery also cannot select the live target, evaluator order,
blackboard values, random outcome, state-machine branch, or Wwise branch for a
particular combat event. WebUI labels must keep authored inputs, recovered
stock-client behavior, and observed live behavior distinct.

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
and bounded Sound/MusicTrack `AkBankSourceData` records. Those source records
separate ordinary Codec media from runtime External Source codecs and generated
Source plugins, while preserving buffering policy, source flags, memory size,
and plugin identity. External/plugin sources are playback sources but are not
promoted into fixed WEM media. Play (`0x0400`) and PlayEvent (`0x2100`) are
traversed, while Stop (`0x0100`) and other control actions are recorded but not
followed. This replaced the former byte-sliding u32 scan, which could climb
Sound parents or follow incidental property, playlist, and switch-map integers
into sibling graphs.

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

Current-build native mapping now closes the common playback path. Named
requests are hashed, `AudioAdapter._PostEvent` allocates an internal playing id
and prepares Event-owned resources asynchronously, then
`_OnEventPreparedDoPostEvent` crosses the same native function-pointer slot as
`AkSoundEngine.PostEvent(uint, ...)` and records the returned real Wwise playing
id. Stop, pause, and resume use that mapping immediately or remain in
`AudioActionQueueHelper` until the real id exists, then reach
`ExecuteActionOnPlayingID`. Animation callbacks route through an entity audio
object or a registered temporary position emitter; ability `PlaySoundAction`
uses the same object/weapon/position paths and retains returned ids for seek,
time-dilation, fade, and stop-on-end behavior. This is exact static call-chain
evidence for the current GameAssembly, not a live execution trace or proof of
the switch/state/RTPC values and media leaf selected by Wwise.

The stock binary also forces the EndOfEvent callback bit on ordinary
`AudioAdapter._PostEvent` requests before forwarding the callback mask to
Wwise; the wrapper preserves caller-supplied optional callback bits and stores
the real playing id through `AkCallbackManager`. This closes the authored
request-to-playing-id callback shape, but not a live callback sample. On the
current CN event inventory, 5,284 Events have typed selector containers; 5,204
graphs are complete and 1,488 have exactly one decoded leaf by topology (1,484
of those have zero unresolved nodes). Audio labels this as a single complete
topology leaf, never as observed runtime playback; the other selector graphs
remain possible-leaf sets until a live state/switch/RTPC/random observation is
captured.

The trigger-specific binary paths are now separated as well. Animation
`AudioAnimationEventReceiver.PostAudioEvent` resolves the target
`AudioObjectMono.audioObjectId`, hashes the authored key, and enters the same
`AudioAdapter._PostEvent` path. `AnimatorBehaviourPlayAudio.OnStateEnter` calls
`GameAction.PlayAudio`, stores returned ids in its playing-id list, and
`OnStateExit` calls `StopAudio` with a 100 ms fade. Ability `PlaySoundAction`
posts its authored `_soundEvent` (or the position/mixing overload) and
`OnEnd` stops its tracked sound instances. These are one authored request per
action; runtime playing-id lists are instances, not thousands of static
options. The internal id, native Wwise id, actual callback order, and active
container leaf remain runtime-only.

The exact Gameplay authored route is now explicit rather than a generic Event
string scan: `Character`/`Enemy` owner -> `SkillData`/`BuffData` action group ->
`PlaySoundActionData` -> `PlaySoundAction.ExecuteInternal` -> `_DoPlaySound` ->
`_DoPostEvent` or `_DoPostEventAtPosition` -> `AudioAdapter._PostEvent`.
`soundEvent` is the authored Wwise Event request; `useTempEmitter`, target and
mount/weapon fields select the object/position route, and `stopOnEnd`, fade,
initial seek, and time-dilation fields govern the retained playing-id
instance. `TargetSettings` still does not reveal which runtime Entity a
selector such as `smart_target` resolves to, and start/end frames are not yet
wall-clock seconds. This is why exact PlaySound actions are stronger than
SkillData-wide Event references. The separate LevelScript route is
`ActionMap` -> typed `PlayAudio`/`PlayAudioAtPosition`/`PlayAudioOnTarget` (or
radio, voice, cue, music, or status actions) -> `GameAction`/`AudioManager` ->
`AudioAdapter._PostEvent`; decoded action presence still does not prove script
execution or branch selection.

Event resource preparation is now bounded more precisely. `_DoLoadEventAsync`
first calls `AudioAssetCache.ActivateAsset(eventId)`. Its false branch calls
the Wwise `LoadBank(uint, callback, cookie, bankType)` overload with the Event
id, a null cookie, and bank type `0x1e`; the bank callback then submits one
Event id to `PrepareEvent` with raw preparation type `0`. The completion path
returns through `AudioAssetHelper`'s waiting callback queue before
`AudioAdapter._OnEventPreparedDoPostEvent` enters Wwise. The activated-cache
branch can bypass that load/prepare miss path. `AkCallbackManager` pumps and
dispatches Event, Marker, Duration, playlist, music-sync, MIDI, and source-change
payloads; callback-info accessors can expose the playing/event/media/audio-node
ids and playlist selection. `AudioAdapter._OnEventCallback`'s exact raw
type-1/EndOfEvent branch calls `AudioAssetCache.DeactivateAsset`: the Event
refcount drops, while pinned Events stay out of ordinary LRU release. Named
`AudioBankManager` `BankHandle` reference counting is a separate bank-lifetime
surface. This proves the static cache/miss and callback topology, not which
optional callbacks a live request registered or which streamed media Wwise
selected.

The targeted current-build GameAssembly bridge audit sharpens this boundary.
Every ordinary `AudioAdapter.PostEvent` overload reaches `_PostEvent`; its
body directly calls `AudioAssetHelper.get_isGcProcessing`,
`_ConsumePendingLoadRequests`, and `_DoLoadEventAsync`, with an internal queue
fallback. `_DoLoadEventAsync` activates the Event asset, can call
`_TryDequeueAndInvokeCallback`, and reaches Wwise `AkSoundEngine.LoadBank` on
the bank-miss path. `AudioAdapter.LoadAndPinEventsAsync` reaches
`_DoLoadAndPinEventsAsync` and the coroutine manager, while
`AudioGameplayStatusSystem._StartDialogEventPreload` reaches that preload
surface and `_OnDialogEventPreloadCompleted` flushes pending dialog events.
The separate `PostEventExternal` path reaches `_PostEventWithExternalSource`
and has a direct `AkSoundEngine.PostEvent` edge after constructing
`AkExternalSourceInfo`; this is not evidence that an ordinary Timeline string
key uses external-source playback. The complete current-build body evidence is
kept in
`reports/story/recovery/audio/audio_runtime_bridge_gameassembly.md` and
`reports/story/recovery/audio/audio_adapter_runtime_gameassembly.md`.
These are static native edges only: they establish the engine's request,
preload, cache, and Wwise boundaries, but not a live C35 activation, callback,
playing id, or selected media leaf.

Playing-id control is separately bounded by the same current build. When the
real Wwise id is not ready, `AudioAdapter._ExecuteActionOnPlayingId` queues
the action; `AudioActionQueueHelper.ConsumeQueue` calls `_ConsumeExecute`,
which resolves `TryGetRealPlayingId` and then reaches
`AkSoundEngine.ExecuteActionOnPlayingID`. The audio-object path is also exact:
`RegisterGameObject`/`UnregisterGameObject` reach the corresponding Wwise
game-object wrappers. This proves the deferred stop/pause/seek control shape,
not that a particular Timeline clip obtained an id or that its stop branch ran.
The focused evidence is in
`reports/story/recovery/audio/audio_control_runtime_gameassembly.md`.

External-source playback is a separate exact path. `PostEventExternal` builds
an `AkExternalSourceInfo` cookie, filename, and codec id, then crosses native
PostEvent slot `0x18f361150`; ordinary Event posting uses `0x18f361158`.
Its EndOfEvent callback removes the external mapping, disposes the temporary
audio object, and releases its Wwise game-object id. This proves the external
file lifecycle but does not identify a live request, filename, decoded file,
or selected playing id.

Music selection is now split into ten exact Wwise State Groups rather than one
generic music label. Current native setters expose the group uint32, state enum
type, method/token/VA, and the shared `AkSoundEngine.SetState(uint, uint)`
boundary. Exact FNV-1 matches recover the authored group names `music_state`,
`music_map`, `music_mission`, `music_cutscene`, and `music_meta`; battle phase,
battle intensity, dialog, login, and remote-communication group names remain
hash-only. Enum ids recover top-level modes, battle phase/intensity, map,
login, meta/gacha, and remote-communication phases. These rows prove the state
vocabulary and write route, not the state active at a captured frame or the
music branch selected by Wwise.

The lifecycle-to-music framework is also static-binary exact. AudioMusicSystem
registers eighteen persistent `StateChangeAction` callbacks as nine paired
masks with action orders 5 and 1: FMV, cutscene, transition cutscene, dialog,
remote communication, loading, teleport loading, fight, and the combined
factory-area/blackbox mask. `AudioStateSystem._OnAudioStateChanged` dispatches
through `HandleStateChange` and `MaskCondition.IsMet`. Metadata-usage delegate
resolution now names all eighteen callback targets, and the current
`SimpleCondition.IsMet` body proves raw condition type 0 is enter and 1 is
leave. `SwitchToDialogMusic` directly writes dialog/top-level Wwise state, and
`_StartBattleMusic` directly writes battle intensity, battle phase, and
top-level state; other callbacks route through recovered cue, timer, loading,
or factory controls. This proves the static registration-to-callback route,
not that a transition executed, its live order, or its selected Wwise branch.

Object selectors and continuous parameters use separate native routes.
`SetSwitch` always carries an explicit entity/GameObject audio-object id plus
group/value ids; typed `AudioId` values are already uints, while the string
overload remains distinct. RTPC setters support global target
`0x00000000ffffffff` and entity/GameObject targets; string names are hashed by
`AudioHashGenerator.Compute`, while typed ids are not rehashed. These default
stock-binary paths cross distinct Wwise native function-pointer slots and may
still be replaced by IFix. They prove setter shape, not the live object,
group/value, RTPC value, timing, interpolation, or selected HIRC child.

Wwise v150 type-6 selector tails are now typed through their full bounded
layout: group kind (`Switch=0`, `State=1`), group/default ids, continuous
validation, value-to-child packages, and 14-byte child associations. Each
association carries `isFirstOnly`, `continuePlayback`, `PlayToEnd/Stop`, and
signed fade-out/fade-in milliseconds; the earlier cross-field
`parameterA/B/C` interpretation was incorrect and has been removed. Clean
value packages often map to strict subsets of reciprocal Children, so a known
runtime group value could narrow the graph. Without that live value and target
audio object, all mapped children remain possible rather than played choices.

Two type-6 groups now have exact current-native setter joins. Group
`0x7acdacaf` is the object-scoped factory remote node-mode Switch; its resolver
maps Normal, Liquid, Gas, mixed, and transition modes to values 1 through 64.
Group `0xf6699cf4` is the global gamepad motion-backend State, with exact XInput
and ScePad setter constants while two other authored values remain unnamed.
Voice-identity, surface/material, and local/remote groups have strong corpus
correlations but no recovered setter, so they remain labeled semantic
inferences rather than authored Wwise names. No live value or chosen child was
observed for any group.

Wwise v150 type-5 Random/Sequence containers now expose the full bounded
policy block and trailing playlist: loop count and modifiers, transition time
and mode, avoid-repeat count, Standard/Shuffle and Random/Sequence modes,
scope/reset/continuous flags, authored playlist order, and per-child weights.
Playlist membership is distinct from reciprocal `Children` ownership: current
banks contain repeated items, empty playlists, and strict playlist subsets,
all with exact bounded tails and no child outside the owned set. Sequence order
therefore comes from the playlist, while owned children omitted by it remain
structural and are not claimed selectable. Weight rows are preserved
independently of the raw flag bit because current banks contain non-default
weights even when that bit is clear. These fields prove the authored selection
policy, while the random seed, shuffle and avoid-repeat history, Sequence
cursor, reset timing, and chosen runtime leaf remain unobserved.

Music Switch and Music Random/Sequence selectors use the same ownership-versus-
selection boundary. A decision tree or music playlist may be a strict subset
of reciprocal Children without making the typed structure partial; selector
leaves outside direct or recursive ownership, including absent object ids,
still fail closed. Extra owned Music Segments remain visible but are not
treated as playlist choices. Live music group values and the audible branch
remain unobserved.

Wwise v150 type-9 objects are Layer/Blend containers. Their bounded tail now
preserves Layer ids, initial RTPC curves, Layer RTPC id/type, child-associated
curve points and interpolation, and continuous validation. A non-empty Layer
proves an authored RTPC-driven blend/crossfade policy, not one randomly chosen
child or unconditional simultaneous playback. Zero-Layer assignments remain
structural Children relations. Children without reciprocal parent pointers are
traversed only when one same-bank audio-node candidate consumes the full typed
tail uniquely, and remain visibly partial; the live RTPC value, child gains,
audible layers, and selected media are not observed.

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
`pathStem` associations. Story-line audio is not a missing-media problem:
existing path-backed `AudioDialog`/voice files can be reused. The remaining
work is to relink each Story line/actor/voice identity to those existing audio
records with correct language, path, and source-graph evidence, then validate
that no link is silently dropped. We do not yet have a complete runtime
receiver, activation chronology, or proof of which branch was selected in a
live game.
The source graph had a concrete ordering gap here: WebUI Story lines were
ingested before structured `AudioDialog` rows, so the shared `audio:<au_*>`
node could exist without the later authoritative path and row metadata.
`tools/endfield_source_graph.py` now backfills that existing node when the
`AudioDialog` row arrives instead of creating a second identity. The Story
line -> existing AudioDialog -> path-backed voice relation is therefore a
supported static join; it still does not prove that the game played that line
or selected a Wwise branch at runtime.
The refreshed follow-up now separates these path-backed joins from Story audio
ids that have no `AudioDialog` path. The remaining set is heterogeneous:
`au_envTalk_*`, `au_radio_*`, `au_sim_*`, and `#N/A` rows may be ambient-text,
owner-table, placeholder, or other event-like inputs rather than missing
decoded voice. They require owner-specific mapping or explicit placeholder
classification; they must not all be counted as failed voice decoding.
The follow-up now records those evidence classes directly: pathless Story ids
can retain exact `DialogTextTable`, `EnvTalkTable`, `RadioTable`, or
`RemoteCommonLine` ownership, while exact Story-id-to-Wwise-event joins with a
Wwise media edge are reported as event/media candidates rather than
`AudioDialog` voice paths. This leaves a clean next split: resolve an existing
owner-specific media path where one is present, or capture the runtime event
and selected media; do not synthesize a voice link from an owner row alone.
The current CN refresh makes this boundary more visible: the Persistent
overlay adds 639 `AudioDialog` definitions for C35/Liino and related content.
Their WEM paths are authored and the corresponding Chinese media is present in
the `AudioChinese` external stream: 607 of those additions decode to playable
media, while 32 zero-duration Liino `*_sv` definitions have no media
candidate. The patched AnimeStudio CLI now merges the primary and fallback
`AudioDialog` tables (while retaining primary-to-fallback chunk resolution),
and the completed CN relink writes canonical `voice/...` paths for those media
ids. The current index has 29,072 AudioDialog definitions, 27,399 playable
entries, and 1,673 zero-duration/no-media rows. `RemoteCommon` remains the
clearest positive separation: a line may carry `audio=au_sfx_remotecomm_*`
while its `voice` and `_debug.source.voiceId` identify a separate path-backed
spoken line. The graph records every explicit candidate with field-level
evidence, preserving the SFX Event/media candidate separately from the
reusable voice file. The generated
`reports/source_graph/voice_audio_links.*` report is the current query surface
for these unique graph edges and their evidence classes.

The residual owner audit is now split by source semantics. RadioTable has 4,995
ordered lines, of which 4,049 have direct playable AudioDialog media and 946
remain unresolved at the base-identity level. A subset of those unresolved
rows has playable protagonist-gender `_f`/`_m` variants; CN conversation output
now exposes those as `audioVariants` instead of treating them as missing media.
The current LevelScript scan proves 2,565 radio action records (2,216
constant bindings and one dynamic binding), but still does not prove action
execution or line selection. EnvTalk has 3,096 rows: 2,807 audio identities,
180 playable rows, five zero-duration AudioDialog rows, and 2,622 identities
without an AudioDialog/media join. These are trigger/owner or source-media
gaps, not reasons to repeat the completed CN decode.
The Timeline audio pass now keeps a separate `levelSequenceAudio`
context for the previously context-free playable Events: current object-index
PPtrs recover `AudioEventPlayable`/`AudioDlgEventPlayable` -> Track clip ->
Timeline parent -> `PlayableDirector`, while active LevelScript union tags
`0x0360`/`0x0361` and exact `_levelSeqId` strings join the parent name after
only the case-sensitive `_Audio` suffix is removed. The join is exact static
identity evidence, not proof that the Director or action ran; rows without a
carrier stay explicit gaps, and Timeline-only/non-LevelSequence parents are
inferred rather than promoted to a LevelScript trigger. Multiple clips and
multiple Director rows are preserved as occurrences, not “options”.
The current CN rebuild scans both complete `StreamingAssets` and `Persistent`
object-index parts and joins raw Timeline JSON only after the serialized
identities are exact, adding clip start/duration and playable stop/fade/seek/2D
controls. It yields 983 target Event identities, all 983 with a Timeline
carrier, 1,476 stored Timeline carrier contexts, and 1,223 Director-linked
contexts. The eight RemoteCommon auto-play Events are excluded from this
Timeline target set because their exact authored route is now represented by
`remoteCommonAudio`; no synthetic Timeline carrier gaps remain for those rows.
The serialized LevelScript scan finds 348
`PlayLevelSequence` records; 232 Event identities have an exact static
LevelSequence-id join, while the remaining action rows are authored inventory
rather than proof of execution.

Four representative trigger contexts now define the intended cross-system
join shape. `Persistent/Data/Json/LevelScriptData/map02_lv002/22800300006.json`
contains an exact `PlayRadioAndWait` for `radio_c27m2_18` (`onlyOnce=true`,
`fromBegin=true`); its RadioTable line 2 resolves to
`au_dlg_c27m2_14_012`, a playable 1.912-second CN file. This is an exact
LevelScript-action -> Radio line -> media chain, but neither action execution
nor line selection is observed. `NpcProxyTable` binds
`changgeng_map02_lv002_e6m1ChengNei` to `envTalk_e6m1_4`; the authored slot 2
actor is `mingbaopu_map02_e6m1ChengNei`, while AudioDialog identifies the
speaker channel as `man_40_07` and supplies a playable 5.386-second file.
Proxy owner, slot actor, and voice channel are therefore three separate
identities; proximity, slot selection, and playback remain unobserved.
Finally, the `au_sfx_cs_c27m4_1` Timeline sample has an authored
`cutsceneTimeline` relation, a complete Wwise `directSound` traversal, and one
decoded media leaf. Its generated row proves the Story key and Wwise
candidate, but not Timeline activation or Wwise posting. The paired
`au_music_cs_tangtang` `levelSequenceAudio` rows are the separate two-carrier
Director/Track/PPtr sample; their non-LevelSequence parent remains an authored
static relation, not a recovered action execution. `dlg_c35m1_10` adds the
fourth shape: 19 exact `DialogTrunk` timeline line schedules, all linked to
existing playable CN `AudioDialog` files, while line playback remains
unobserved.

The surrounding C35 activation composition is now recovered exactly enough
to separate root playback from the audio lane. The root
`CutsceneRootComponent` (`_timelineName=dlgtl_c35m1_10_sub_1`) points through
`_director` to root PlayableDirector PathID `63140722070379897`, whose
PlayableAsset is the root TimelineAsset PathID `-2466791841398753755`. The
root Timeline's `Audio` ControlTrack contains one `ControlPlayableAsset` clip
from `0.0s` to `180.583333s`, with `autoBindingPath=Audio`,
`updateDirector=1`, and `active=1`. That binding selects the child GameObject
`Audio` and its PlayableDirector PathID `79300700487540089`, which points to
the C35 Audio TimelineAsset PathID `6744480576528724800` containing the 21
SFX placements. This is exact serialized root/ControlTrack/child-Director
composition, not live execution or a Wwise PostEvent. The small separate
Director carrier that also points at the Audio TimelineAsset remains a
duplicate source occurrence without a recovered root receiver.

The CN builder now writes `audio/trigger_contexts.json` (trigger-context schema
5, Audio index schema 32) with 14,244 rows: 431 `dialogLifecycle`, 5,602
`dialogTimeline`, 3,001 ordinary `envTalk`, 95 separate `envTalkGreeting`,
3,120 retained LevelScript/Radio media associations, 8 exact
`remoteCommonAudio` auto-play rows, and 1,987 Timeline contexts. 9,434 rows
have a real playable `src`; runtime execution is observed for zero rows. Of
the Timeline rows, 808 are authored keys that
are not present in the current Wwise/Event index and therefore intentionally
have no media reference. Coverage is explicit in the shard: Radio has 4,995
conversation line ids but only retained action/media rows are projected, and
unresolved lines remain in
`triggerCatalog.levelScriptRadio.unresolvedRadioLines`. Every row keeps
independent definition, owner/selection, media, and runtime evidence; no
single confidence value upgrades a static relation into a played sound.
The static Timeline runtime-contract coverage is now 1,476 rows: 278
`AudioDlgEventPlayable`, 388 `AudioEventPlayable`, and 810
`AudioMusicPlayable`. The other 511 rows are Story cutscene `audioEvents`
references rather than unidentified Playable objects: 421 remain
`storyCutsceneAudioReferenceOnly`, while 90 share an Event ID with a serialized
Timeline carrier. This distinction prevents a Story-level reference from being
reported as an exact Track/Playable join.

The 95 `greetEnvTalk_*` rows were previously filtered because their generated
conversation payload is marked `misc`; the exact `EnvTalkTable` line-to-audio
relation now uses `envTalkGreeting` while retaining unresolved proxy/slot
ownership and runtime selection. Eight `RemoteCommonTable` rows with
`autoPlay=true` now use `remoteCommonAudio`: `remoteCommSingleDataList[*].audioId`
is an exact Wwise SFX Event/directSound candidate, while the row's `voiceId`
stays a separate dialogue identity. Duplicate authored greeting occurrences
retain unique `:lineN` trigger IDs instead of collapsing into one context.
Those eight Events are also present in the Audio event summaries as
`remoteCommonAudio` / `authoredConfig` with
`exactRemoteCommonAudioId`; they are no longer synthesized as
`timelineCarrierMissingFromCurrentObjectIndex` gaps.

The source graph now ingests this shard as first-class `audio_trigger_context`
nodes. It retains reverse context-to-audio and context-to-Wwise-event edges,
plus exact joins to Story lines, Radio rows, EnvTalk rows, and Timeline rows
when those identities exist in the graph, including `remote_common` and
`remote_common_line` rows for the auto-play surface. These edges are static authored
candidate evidence; a missing context edge or a present Wwise edge still does
not prove that a runtime branch executed or that a sound was audible.

The Timeline coverage also publishes stable static runtime-contract ids for
the three named string-key playable carriers and a method/field catalog; these remain
metadata evidence, not observed execution. `dialogLifecycle` is now a separate trigger surface over all five
`AudioDialogCustomEventTable` arrays: preload, pre-enter, post-enter,
pre-exit, and post-exit. The current table contains 431 authored values across
206 dialogs; 429 values join a current Wwise Event object, but 413 have no
decoded media leaf and two values remain unresolved. Static metadata for
`Beyond.Gameplay.Audio.AudioGameplayStatusSystem` identifies the matching
pre/post dialog handlers plus `_ScheduleDialogAudioEvent`, preload completion,
and pending-event flush methods. For `dlg_c35m1_10`, the exact hooks are
`postEnterEvents[0] = 0x4cd598ce` and `preExitEvents[0] = 0xcd4ea851`.
These facts prove an authored lifecycle request/scheduling contract only;
dialog-state dispatch, `PostEvent`, Wwise branch selection, and audible output
remain unobserved.

The Timeline playable audit now records separate static runtime contracts for
the three named carriers. `Beyond.Audio.AudioDlgEventPlayable` exposes
`OnManualFixBehaviourPlay`, `ShouldPlay`, `_DoPlayEvent`, pause/graph-stop
cleanup (`_DoPlayStopEvent`/`_TryStop`), and jump/seek methods; its serialized
controls include cue mode, optional stop key, fade/seek, binding, 2D, and
emitter fields. `Beyond.Audio.AudioEventPlayable` exposes the corresponding
play/pause/graph-stop surface plus `_TryPostExitEvent`, `MarkSkip`, and an
`_exitAudioEvent` `AudioId`. These are static IL2CPP method/field surfaces, not
an observed call order or Wwise request. The distinct
`Beyond.Gameplay.Core.DialogAudioEventPlayableAsset` uses an integer
`AudioId` with `OnClipEnable`/`OnClipDisable`; it must not be merged with the
C35 string-key SFX lane. `Beyond.Gameplay.Audio.AudioMusicPlayable` adds the
music carrier fields `_audioEventKey`, `musicActionType`, and `triggerOnSkip`;
its matching behaviour exposes `OnBehaviourPlay`, `_ShouldPlay`,
`_TriggerEvent`, and `OnTimelineSkip`, but the call order and live music-state
selection remain unobserved. The current raw JSON join restores both
`musicActionType` and `triggerOnSkip` for 767 of 810 music carriers; the
remaining 43 have no serialized value. Current metadata resolves
`musicActionType` as `DIALOG_MUSIC=0`, `NORMAL_MUSIC=1`, and `CUSTOM_MUSIC=2`;
`triggerOnSkip` is a bool (`0=notTriggeredOnSkip`, `1=triggeredOnSkip`). These
are serialized control meanings, not proof that a skip occurred or that the
corresponding music state was accepted. Semantic schema 32 / trigger-context
schema 5 now stores these per-carrier controls, stable contract ids, and the
full static contract catalog while keeping runtime execution unobserved.

The same serialized Timeline scan now handles `AudioCuePlayable` separately
from Event playables. Twelve cue carriers (eleven cue names) join exact Track,
Timeline-parent, and five PlayableDirector identities; seven cue definitions
resolve through the native AudioCue hash and yield eight downstream behavior
Event contexts, while five remain explicit missing-definition invocations.
Cue names are not synthesized as Wwise Events: cue conditions/handlers,
Timeline/Director activation, AudioCueSystem execution, and Wwise branch
selection remain unobserved.

Playable skill linkage is recorded per Event instead of inheriting a whole
group’s confidence. An exact Gameplay action id joined to the same SkillData
file proves an authored dependency; a complete length-prefixed Event reference
in that file is `skillDataEventReference`, while an exact
SkillData-to-BuffData reference walk is `skillBuffChain`. This generic scan
does not recover the containing field or callsite. Child-skill family-prefix
placement remains inferred. Dependency-only paths retain
`conditionAndTimingUnresolved`; only the decoded action families below prove a
request operation and authored timing.

The current BuffData MemoryPack union identifies `PlaySoundActionData` at tag
`0x010d` with 22 serialized members (the common action prefix plus 18 sound
fields). Sixteen authored occurrences across 13 unique Events now decode
through an exact action boundary from 23 source files, with zero decode
failures. They preserve start/end frames, enabled/priority data, interrupt and
initial-seek milliseconds, stop-on-end/fade lifetime, temporary-emitter and
target/mount/weapon routing, and time-dilation pause/seek controls. IL2CPP
metadata independently validates the 18 fields and the runtime
`PlaySoundAction` lifecycle that stores playing ids, posts on an object or at a
position, seeks, ticks, and stops retained instances on end. All 13 exact Event
names hash to current Wwise Event objects and resolve to decoded media. Fifteen
actions link to a Gameplay owner; the remaining
`buff_chr_0030_zhuangfy_combo_skill_target_mark` action is an explicit owner
gap rather than a decode failure. The remaining `TargetSettings` payload is
only byte-bounded, authored frames are not converted to wall-clock time, and
the runtime activation condition remains unresolved. The Gameplay page therefore
places only exact skill-config Event references back on their skill rows, leaves
inferred links in the final audio section, and never duplicates one Event
between those placements. The Audio view exposes exact/inferred trigger
filters, a separate authored-PlaySound-action filter, and the recovered action
lifetime/routing evidence. Owner selection for the unresolved action remains
unproven; it is not guessed onto a skill.

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

Current-build LevelScript audio ActionBase layouts now decode from their exact
union tag/member count and generated-setter field order. The overlaid corpus
has 4,611/4,611 ActionBase records decoded: 1,461 constant Event-request
contexts, 291 named AudioCue invocations, 22 dynamic Event parameters, and 390 typed music/
state/variable/stop/control records. Newly bounded families include auto-music
blocks, battle-music blocks, custom music mode, PlayVoice and
PlayVoiceNarrative, PostAudioCueOnRelease, and three zero-field controls
(`ExitCustomMusicMode`, `FlushRadio`, `PostAudioStopAllEnemyVoice`) whose
ActionMap framing is exact. Same-tag getter/header rows are rejected by their
ActionMap membership (231 former `AnnounceAudioOnTarget` false positives).
Constant Events receive exact
script/action/role/routing contexts in Audio. Cue names, dynamic parameters,
playback handles, placeholder-music ids, and state/variable writes remain
typed control records when their runtime value is unresolved; no name or live
value is synthesized for them. Native `AudioCueSystem.PostCue(string)`
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

The same Persistent-over-Streaming UID census finds 5,075 rows whose numeric
tags have audio/radio/music/voice/cue formatter names. A bounded
`actionMapMembership` check classifies 233 of these as same-tag collisions in
getter/header lists rather than ActionBase playback records: 98
`BlockAutoMusicChange` member-count-10 getter rows, 6
`BlockAutoMusicChangeCancel` member-count-18 header rows, 18
`CleanAudioCueVar` getter rows, 3 legacy `EnterCustomMusicMode` header rows,
and 108 legacy `Play3DRadio` getter rows. They remain outside the audio-action
index until their owning union is independently decoded; no Event is inferred
from the numeric tag alone.

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
2,565 current records: 2,216 constant radio-id bindings and one dynamic binding
remain explicit. RadioTable contributes 2,948 definitions and 4,995 ordered
lines; 3,129 referenced lines join 3,120 stored trigger contexts through exact
`audioDialogPath` stems, while 404 referenced lines remain unresolved. The
table-wide direct-media surface is 4,049 decoded lines with 946 unresolved
base identities; playable `_f`/`_m` variants are exposed on the owning WebUI
line rather than promoted to a false base match.
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

Timeline music ownership is now order-independent across both complete Unity
object indexes. Together with AudioEvent/AudioDlgEvent/Cue carriers, the CN
semantic rebuild has 1,476 Timeline carrier contexts and 1,223 exact
PlayableDirector-linked contexts; raw clip timing/control joins cover 1,488
serialized playable placements. These are serialized ownership joins only:
Director activation, cue execution, Wwise state values, branch selection, and
actual playback remain unobserved.

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

Current controller and selector audits sharpen two boundaries. Unity
`AnimatorController` state-machine membership now joins `m_AnimationClips`
slots to authored state/state-machine paths (46,755 local state references in
1,246 controllers), but PathID reuse across CABs and missing override joins
mean this is authored membership, not current-controller execution. Native
`AudioRemoteFactoryBridge.UpdateNodeMode` resolves the seven NodeMode inputs
1/2/4/8/16/32/64 to Wwise values `normal`, `liquid`, `gas`, `gasliquid`,
`gastrans`, `liquidtrans`, and `solidtrans` respectively; a zero resolver
return skips `SetSwitch`. This is exact setter/value mapping, while the live
NodeMode and selected Wwise branch remain unobserved.

The music catalog now records all ten managed music-state groups with exact
enum-member hash values and static native callsites: battle start sets combat
general/main-loop/high, leaving fight sets low, main-game/loading sets loading,
dialogue sets dialogue plus dialog-none, and remote communication ends with its
ending state. ManualSetMusicState, ManualSetBattleMusicState, and
ManualSetBattleMusicIntensityState route to Wwise with caller-supplied values,
so their live state remains unknown. AnimatorOverrideController recovery adds
2,046 replacement clip slots (435 effective audio clips, 847 callback rows),
but missing serialized-file envelopes and runtime activation keep those joins at
corpus PathID reachability rather than exact live-controller ownership.

The current audio-recovery queue is ordered by evidence value:

The bank-coverage pass now enumerates both StreamingAssets and Persistent VFS
indexes. The current CN build certifies nine SHA-256-locked PCKs: the main,
CN-language, Audit, and Init banks plus five HotfixAudio packages. Hotfix adds
typed HIRC evidence to 28 already-authored/hash trigger rows, including E11M1
cutscene and projectile events. Its 207 Event objects include 42 matches among
the complete 7,975-name WebUI Event corpus, but none of the C35 scene-10 keys;
those keys are therefore exact AudioHashGenerator hashes absent from this
fingerprinted current bank set, not simple filename misses. The generated
audit is `reports/story/recovery/hotfix_audio_event_audit.{json,md}`. The
Persistent-primary targeted decode now certifies all 402 Hotfix media ids
(94,801,428 FLAC bytes) in shared browser storage: 11 are new physical ids and
391 replace an existing base-package id. The normal index labels all 402 as
HotfixAudio. Package-family media resolution closes eight language-bank
relations: 164/207 Event objects reach media and 383/402 media ids have a
Hotfix-local Event hash. Of the remaining 19, named Events in other scanned
banks recover 12. Complete traversal of all raw Event objects recovers the
last seven through four unnamed base-bank hashes: `0x1efefa3c`, `0x0e8882e2`,
`0x60721bf3`, and `0x212b3577`; no Hotfix media id now lacks an Event-object
playback relation. The 165 Hotfix Events
without authored names split structurally into 154 media-playback graphs, six
control-only graphs, four partial same-bank object graphs, and one graph with
no media leaf. Language-bank HIRC graphs remain isolated; only their media
lookup is joined to `hotfix_main.pck`, avoiding cross-bank object-id collisions.

Installed Lua is now decrypted from both VFS roots with Persistent precedence
per logical path. The current corpus has 552 direct `PostEvent` callsites over
377 unique `au_*` names; 369 hash to current Wwise Event objects and eight do
not. RTPC, AudioCue, and indirect literals remain separate. Exact source line
and expression are retained, but static presence does not prove that the Lua
branch ran.
The repeatable audit is
`reports/story/recovery/lua_audio_event_audit.{json,md}`. All eight unresolved
Lua hashes are absent from every one of the 21,124 current unique Event
hashes, rather than merely missing from the named subset. Close spellings and
resolved same-file sibling Events remain review evidence only; no alias is
promoted without a binary or authored identity source.

The full nine-PCK inventory contains 21,712 Event-object occurrences over
21,124 unique hashes. The semantic Audio view now includes all of them:
12,183 hashes still have neither an authored name, numeric trigger field, nor
trigger callsite; 1,259 hash-only Events have an authored numeric context; the
rest have recovered names. Exact equality between an `AudioDialog` path hash,
its signed voice id, and a current type-4 Wwise Event id validates 1,213 voice
aliases without fuzzy matching. Of those, 1,199 restore names that were
previously absent. `ResponsiveDialog` places 1,084 of these Events in 4,020
authored speaker/trigger response slots, while `AudioVoTone` contains 81 Event
variants. The repeatable audit is
`reports/story/recovery/audio/voice_response_audio_event_audit.{json,md}`.

Current metadata types the voice-table strings more narrowly than a generic
table hash scan: `SpeakerChannelData` exposes `narratingWwiseEvent` and
`radioWwiseEvent`, `VoiceData` exposes `overrideWwiseEvent`,
`ResponsiveDialogTriggerData` exposes `eventTemplate`, and
`AudioDialogConfigs` exposes its default/mono override Events. Requiring one of
those typed fields plus exact current type-4 Event-id equality recovers 1,397
aliases, 1,393 of them newly named: 650 narrating-channel Events, 650 radio
Events, 31 per-definition overrides, 65 response templates, and two defaults.
`VoiceManager._SpeakNarrative` calls `VoiceUtilsInternal.SelectWwiseEvent`,
which writes the selected Event into `VoiceContext`, before
`VoicePlayer.PlayVoice`; this proves the route but not the live branch choice.
Of these Events, 1,396 lead to a typed Wwise External Source and one has no
recovered source, so no decoded media is fabricated. The repeatable audit is
`reports/story/recovery/audio/voice_table_audio_event_audit.{json,md}`.

Six additional current table-field families have both metadata getters and
exact decrypted-Lua consumers: `ActivityTable.bgm`,
`ActivityPushPopupTable.bgm`, stamina-refund `audioOnOpen`, gacha/skip-chapter
`videoAudioKey`, and the five `DomainData.audKey*` fields. Exact current Event
hash equality recovers 21 names: two activity-center BGM, four push-popup BGM,
two panel-open, three synchronized video-audio, two region-switch, and eight
domain-upgrade animation Events. `VideoPlayer.PlayAudio` posts the Event,
stores its playing id, stops by playing id, and seeks the Event when video time
drifts; the selected video and live execution remain unobserved. Eighteen
Events reach 22 decoded media candidates. The other three music-control Events
contain only serialized Set State (`0x1200`) / Reset Game Parameter (`0x1400`)
Actions, so they are control-only rather than playback with missing media. The
complete Event inventory now classifies 17,828 playback, 688 mixed
playback/control, 1,727 control-only, and 2,530 unresolved Action roles. The repeatable audit is
`reports/story/recovery/audio/typed_ui_audio_event_audit.{json,md}`.

The same bounded audit also admits two `SNSDialogTable` strings that were
previously excluded as generic positional parameters. Current metadata fixes
`SNSDialogContentType.Voice=5`; only those two nodes use type 5, and decrypted
Lua maps that content type to `SNSContentVoice`, reads `contentParam[0]` as the
Event, posts it on click, and stops its playing id on the authored four-second
timer or widget disable. Each Event has one decoded media leaf. Other SNS
parameters stay excluded because they do not establish this audio-consumer
route; the six `NumIdStrTable` skill-name/hash matches remain excluded from
trigger placement for the same reason.

The six `NumIdStrTable:skill_id` matches are now retained as identity-only
aliases rather than discarded: each dictionary string exactly names a
same-name `SkillData` file and hashes to a current type-4 Wwise Event. Five
Events reach 13 decoded media leaves and one has a Play root without decoded
media. A bounded scan of all 10,161 `SkillData`/`BuffData` files
(48,266,925 bytes) finds zero serialized uint32 occurrences of the six Event
hashes, and current metadata exposes no generic Skill-to-audio consumer.
Therefore these rows recover Event names and SFX identity, but deliberately add
no trigger context, owner, or playback location. The repeatable audit is
`reports/story/recovery/audio/skill_id_audio_event_audit.{json,md}`.

Current-build native control flow independently preserves the boundary:
`VoiceManager.Response` reaches `VoiceResponseProcessor.Response`, selection
queues a response, and `VoiceSpeakChannelProcessor._PlayVoice` reaches
`VoicePlayer.PlayVoice`. The voice context carries handle id, audio object id,
and Wwise Event; `VoicePlayer` then has distinct Event and External playback
paths. `ApplyRandomVoiceTone` can replace the voice id through
`TryReplaceVoiceIdWithTone`. Therefore response membership proves a possible
authored trigger family, tone membership proves only a selection transform,
and an `AudioDialog` definition alone is not a playback location. The compact
table/binary audit and current-build metadata/GameAssembly reports live under
`reports/story/recovery/audio/`.

This changes decoded-media placement from 27,556 fully unknown files to 615.
After adding responsive, typed UI, and SNS Voice trigger contexts, 38,775 media have
authored Event context and 20,329 remain honestly separated as Event-related media whose
authored trigger placement is still unknown; 27,399 direct dialog media retain
their stronger classification. The generated index also suppresses 2,237
byte-identical `wwise/unknown` path occurrences that have a stronger
same-storage categorized copy. It does not delete the physical files or merge
same-id rows whose bytes differ. The two Hotfix/category same-id groups
(`291650974` and `522607827`) have different bytes, remain as distinct players,
and inherit the exact `au_music_main` relation because HotfixAudio replacement
uses the same numeric Wwise media id.

The final seven shared unknown-location files are not unparsed library blobs.
Each is an exact version-150 type-2 Sound codec-media object. Five sit below
two type-5 containers (`74630620`, `824607808`) and two sit below type-9
container `144808260`; the only Event/Action graphs in those embedded banks do
not reach these branches. WebUI therefore labels them as resolved Wwise Sound
definitions without an Event path while keeping playback location unknown.
The remaining 608 unknown-location rows are CN language External Source files,
which must not be attached to one of the 1,396 External Source Events without
an authored voice-selection identity.

1. Use the new bounded live-session capture path in
   `scripts/story_recovery/capture_audio_runtime_trace.py` and normalize its
   JSONL with `import_audio_runtime_trace.py`. The hash-locked current-build
   manifest samples Gameplay `PlaySoundAction`, LevelScript `PlayAudio*`,
   Timeline audio carriers, `AudioAdapter.PostEvent(string)`/`_PostEvent`, and
   playing-id
   controls. It establishes carrier -> Adapter request evidence and joins
   numeric Event hashes or string keys to static name/media and trigger-context
   candidates; `--check-only` is verified, but no live session has been
   imported yet. The importer reports static join status separately from
   `runtimeEvidenceStatus`, which is only `verified` when the attached module
   path and size match the hash-locked GameAssembly. Wwise acceptance, selected
   media, callbacks, and audibility remain the next runtime boundary.
2. Finish owner-specific trigger/media audits after the CN path-backed
   AudioDialog relink. Prioritize Radio base-to-`_f/_m` variants, the 404
   LevelScript-referenced Radio lines without direct media, the 1,673
   zero-duration AudioDialog rows, and EnvTalk identities without an
   AudioDialog/media join. Keep pathless `DialogTextTable`/`EnvTalkTable`/
   `RadioTable` ownership separate from playable paths, and do not decode or
   invent replacement media when an existing audio record is available.
3. Use the unified `triggerContext` surface to close the remaining authored
   trigger/media gaps. Prioritize the 808 Timeline keys missing from the
   current Wwise index—especially the 21 C35 scene-10 SFX placements across
   18 keys. The C35 root `CutsceneRoot` → root Director → Audio ControlTrack
   → child Audio Director chain is now exact; next resolve whether those
   authored keys belong to an older/alternate Wwise bank or only to stale
   Timeline data, without synthesizing media or claiming runtime execution.
4. Promote only exact Wwise event/media candidates to a separate playable-event
   surface after verifying the shared-media path and event payload; they are
   not Story voice links merely because the names match.
5. Finish bounded static joins with high downstream value: PlaySound
   `TargetSettings` and condition semantics, Timeline/PlayableDirector audio
   receivers, AudioCue handlers, current music-table state/control to
   MusicTrack sources, and LevelScript bark/response families only when their
   serialized layouts are proven.
6. Recover authored trigger identities for the 12,183 raw Wwise Event hashes
   that currently have only library-object/media evidence, and resolve whether
   the eight direct Lua `PostEvent` names absent from all current banks are
   stale requests, misspellings, or references to another bank version. Do not
   alias by name similarity. Preserve the structural roles of the 165 unnamed
   Hotfix Events, add bundle/channel-level decode certification, and keep the
   four known language-bank crowd/voice families distinct from runtime locale
   selection.

The exact current UID/actionMap census has no `actionList` rows for
`PlayGlobalResponseVoice`, `PlayResponseVoice`, `PostAIBarkEvent`,
`TriggerBarkVoice`, `TriggerMainCharVoice`, `SetAudioGlobalParameter`, or
`SetAudioParameter`; these remain runtime-capability/Lua-candidate surfaces,
not authored LevelScript Event links.
After those four queue items, Gameplay follow-up should finish the partial
`EnemyData.AbilitySystemData` mode-tail
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
- Active IFix/server combat overrides, patched processor arithmetic, live
  target selection, evaluator chronology, and evaluated blackboard values.
- Additional family-specific MemoryPack/FlatBuffer schemas.
- Deep semantic decoding of byte-bounded Buff EffectActionCfg and
  IgniteEventAction bodies, plus remaining Skill smart-target and
  SwitchToBuffConfig inner payload fields.
- Broader exact world-streaming scene decoding.
- Runtime projectile spawn/call-site ownership, evaluated blackboard values,
  remaining unnamed projectile enums, and Wwise container selection.
- More exact joins between gameplay identities and runtime assets.
- Per-system negative/certification reports that fail visibly when inputs
  change.

Changing counts belong in `reports/`; durable conclusions belong here.
