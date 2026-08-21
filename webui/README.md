# WebUI

`webui/` is a static research browser over generated Endfield data. It has no
application build step: serve the repository and open the default local URL.

## Run

```bat
python serve.py
python serve.py 9000
```

Reuse `http://127.0.0.1:8765/` when it is already running. A custom port is for
an explicitly separate server.

## Pages

| Page | Scope |
| --- | --- |
| Story | Reconstructed dialog, SNS, radio, options, cutscenes, media, and evidence-typed order |
| Characters | Identity groups, source evidence, related assets, and live overrides |
| Gameplay | Characters, equipment, enemies, items, progression, skills, projectiles, assets, and sound |
| Audio | Wwise Events/media, authored contexts, decoded playback candidates, and recovery state |
| Assets | Exported images, models, materials, video, and metadata |
| Text | Searchable localized table/reference rows |
| Updates | Exported game-data changes between two complete versions |
| Mission Pipeline | Experimental debug-only mission/Story evidence |

Factory, World, Presentation, Progression, and standalone Combat & Projectiles
pages are retired. Useful progression, projectile, and sound information lives
in Gameplay.

## Frontend map

- `index.html`: application shell and page containers.
- `style.css`: shared layout, responsive behavior, and media presentation.
- `app.js`, `app_tree.js`, `app_labels.js`: Story/Text rendering and labels.
- `reference.js`: localized Text Tables browser.
- `assets.js`, `updates.js`: Assets and Updates pages.
- `src/features/characters/`: Characters view and runtime overrides.
- `src/features/gameplay/`: Gameplay datasets and sound players.
- `src/features/audio/`: Audio evidence browser.
- `src/features/mission_pipeline/`: debug-only Mission Pipeline.
- `src/features/map_recovery/`: debug-only experimental world-coordinate map recovery for every level that owns a plotted node; the map surface is full-bleed with the title/metrics, controls and inspector as draggable, collapsible floating panels, and the page shows one whole region at a time - every sibling zone's map screen tiles onto the same world surface with no frames between zones, so panning crosses zones seamlessly.

Generated data belongs in `webui/data/`; user-managed inputs belong in
`webui/overrides/`. Do not hand-edit generated JSON.

## Data layout

Core generated outputs:

```text
webui/data/manifest.json
webui/data/lang/<LANG>/index.json
webui/data/lang/<LANG>/conv/*.json
webui/data/lang/<LANG>/mission/*.json
webui/data/lang/<LANG>/reference/**
webui/data/lang/<LANG>/characters/index.json
webui/data/lang/<LANG>/gameplay/**
webui/data/lang/<LANG>/gameplay/projectile_audio.json
webui/data/lang/<LANG>/audio/{index,events,media}.json
webui/data/gameplay/projectiles.json
webui/data/mission_pipeline/index.json
webui/data/mission_pipeline/missions/*.json
webui/data/map_recovery/index.json
webui/data/map_recovery/maps/<levelId>.json
webui/data/map_recovery/render/*.{json,png}
webui/data/assets/{index,gameplay_refs,story_media,videos}.json
webui/data/updates/latest.json
```

Builders may add compact sidecars, but each page must tolerate an absent
optional sidecar and display an explicit degraded state when the omission
matters. Schema changes must be coordinated with their frontend consumer.

`data/gameplay/projectiles.json` owns immutable projectile behavior and authored
event hashes. The language-specific `projectile_audio.json` sidecar owns decoded
media candidates; Gameplay joins it by projectile id, sound field, and unsigned
event hash without writing audio rows back into the behavior payload.

`data/assets/gameplay_refs.json` is also Gameplay-owned: the `asset-refs` stage
joins the current Gameplay index to the Assets-owned broad index. The Assets
builder never writes this consumer-specific sidecar.

## Shared behavior

- Normal navigation exposes Story, Characters, Gameplay, Audio, Assets, Text,
  and Updates.
- Mission Pipeline appears only while `Show debug info` is enabled. Turning
  debug off while it is active returns to a visible page and normalizes the URL.
- Debug state controls raw source blocks, recovery evidence, Mission Pipeline,
  manual Story-order tools, and unresolved ownership details. Story issue and
  recovery-method filters remain visible in normal mode.
- Missing optional data is a visible unavailable/degraded state, not an empty
  success state.
- Filters, keyboard focus, modal behavior, and large result sets must remain
  usable on narrow and wide screens.

## Story and media

Story combines authored dialog structures, Timeline evidence, mission/runtime
links, localized references, and manual order. Evidence types stay visible;
weak proximity or naming matches never become exact chronology or ownership.

Stable contracts:

- Reset returns to Story sort and default filters while preserving expanded
  mission groups.
- Source/debug blocks, Timeline evidence, cutscene diagnostics, and order-edit
  controls remain debug-only.
- `sns_emoji_*` renders as ordinary inline emoji without hover or modal preview.
- Other SNS images and stickers keep their natural proportions with bounded
  hover and modal previews.
- Definitions, authored placement, runtime activation, and observed playback
  are distinct states. A media definition does not prove that it played.
- Cutscene presentation shapes remain distinct: rooted Timeline, component-only
  Timeline, LevelScript FMV, mixed carriers, and text-only candidates are not
  silently merged.
- Subtitle text is attached only through an exact authored link or a unique,
  complete ordered match. Partial or ambiguous matches fail closed.

Manual inputs:

- `overrides/story_order.json` is the active user-managed order. Export tools
  never replace it.
- `data/story_order_ocr.json` contains OCR proposals only.
- `overrides/options.json` stores manual option placement/response recovery.
- `overrides/narrative_videos.json` controls inline video attachment,
  suppression, and optional audio inheritance.

## Characters and Gameplay

Characters merges table, Story, and asset identities while retaining source
provenance. Merge/name overrides are live inputs written through `serve.py` and
do not require a rebuild. Debug-only controls must not leak into normal page
navigation.

Gameplay owns character progression, equipment, enemies, skills, projectiles,
assets, and compact sound players. Evidence labels distinguish exact authored
ownership from family-, animation-, or identifier-inferred placement.

- Enemy level selectors show only authored level points; missing levels are not
  interpolated.
- Enemy variants may share an attribute template while retaining different
  buffs, modifiers, AI, or assets.
- Positive authored skill cooldowns are shown at the selected skill level.
  Enemy born-Buff cards expose exact BuffData lifecycle, stacking, trigger,
  keyed-value evidence, exact attribute modifiers, and raw applied tag ids.
  The current GameplayTagPredefineTable and serialized GameplayTagConfig
  object-index paths are joined by exact signed-Int32/unsigned-hex IDs (the
  config path CRC32 rule is build-evidence-backed), so known tags show their
  names and context. Missing immunity paths are named only when an exact
  `tagName2Immune` status context independently proves the `Immune/<suffix>`
  CRC32; those rows remain marked as context-derived evidence. Other unmapped
  IDs retain their raw value and expose why the current serialized registry
  did not resolve them on hover. Fully
  validated current-build runtime captures can be supplied to the Gameplay
  base builder to add exact tag-id/name observations that are absent from the
  serialized registry; runtime-only rows remain marked as runtime evidence.
  consumed non-empty action chains show the gated current event name and the
  decoded action fields, including actions nested under If/Else branches.
  Current visible families include skill/global cooldown checks and changes,
  Buff-id/stack/HP/poise/damage/tag/distance conditions, timed markers,
  resource changes, blackboard operations, skill casts, interactive coins,
  effect ids, created/finished Buff ids, bounded damage actions, and target
  selection. Common TargetSettings fields (target/group, context, owner,
  source, and selector values) are shown even when the enclosing action is
  partial. Blackboard calculation rows label the native HpRatio type and all
  current operations, including Floor, Ceil, and RoundToInt. Complex entity
  ConvertToTargetContext rows label the current target-conversion and
  translation-rotation modes. CompareFloat actions show exact blackboard
  comparisons. SimpleCalcBBAction displays its decoded operation rather than
  assuming division. SpellInfliction rows label their elemental type.
  Complex entity spawn, projectile, heal-calculation,
  DamageUnit/EffectActionCfg, and unresolved selector payloads stay visibly
  unresolved.
- Enemy attribute modifiers show their current native enum meaning and raw
  authored value. The page does not synthesize a final combat value across
  other buffs or the runtime IFix branch.
- Projectile templates, spawned behavior, and playable-skill ownership remain
  separate relations.
- Character-skill and enemy SFX players are collapsed compactly. Inferred
  ownership is labeled; raw identity, matching, and unresolved candidates are
  debug-only.
- Shared animation Events are global Wwise graphs unless a stronger owner edge
  exists.

## Audio

Each Event and media record accepts a manual note in its detail pane. The user
must explicitly select Save note; typing alone never writes the override or
updates search/list state. Saved notes are
keyed by language and record identity, persist through
`overrides/audio_notes.json`, and are included in the existing text search. The
first note line is shown beside the record filename in the list. These user
annotations are not generated game-data evidence.

In a selected Audio record, the playable-media section is rendered first,
before Details, manual notes, and the longer evidence list.

Expanded Audio-page files load with their waveform visible by default. Groups
with more than 20 possible files retain lazy collapsed players and load each
waveform only when that file is expanded.

Audio keeps four layers separate:

1. authored Event or media identity;
2. Wwise graph relation and possible media leaves;
3. authored consumer/trigger context;
4. observed runtime execution or selected branch.

Only the available layer is claimed. Exact HIRC traversal can prove possible
media but not switch/random selection or audibility. String literals and
same-name assets remain identity evidence until a typed consumer reaches a
playback API. Fingerprint-locked native evidence fails closed after a client
update.

Serialized `monoBehaviourAudioIdField` contexts expose searchable authored
field roles (`componentSoundSpawn`, `componentHitCallback`, finish/state,
water/particle roles, or the generic serialized-field boundary (with an
audio-key hint)), their `componentLayout`, component type, and raw serialized path.
The detail evidence also shows the existing exact GameObject hierarchy and
world position when present. These are authored field projections only; the
page does not label a field as executed, posted, selected, or audible. Role and
Event coverage counts come from generated summaries and are not hard-coded in
the frontend.

Scene-emitter details keep prefab source/status separate from scene ownership.
Prefab-local containment and scene-asset candidates are displayed as distinct
static evidence; only an exact, unique candidate with an authoritative
`sceneId` may be shown as scene-owned. The generated row contract retains the
source and `sceneOwnershipStatus`/`sceneContainmentStatus`, with
`sceneId`/`sourceName`/`sourcePath` only on an exact scene containment row.
Missing or malformed AssetMap input is shown as unavailable rather than
replaced by a name/path guess. A prefab source row is not a recovered level
instance.

Streaming-instance rows expose their exact entity/name/transform and bounded
raw ECS evidence separately from prefab identity. The current validated
InitChunkData schema has no known prefab Source+PathID/hash field, so the Audio
page leaves level ownership unresolved unless a future exact numeric identity
resolves to one unique full AssetMap container path or explicit component
identity. Basenames, names, positions, Meshes, and similarity are never search
or ownership evidence; StreamingChunkData correlation remains an explicit gap.

AudioCue AST detail is lazy and debug-only. It exposes the validated tree's
source coordinates, parent/depth, `exprType`, four scalar fields, child paths,
node class, semantic role, and bounded diagnostics. Non-empty behavior
`exprType=3` is an authored Event request; non-empty `exprType=8` is a
`runtimeCueVariable`; non-empty children are `compositeOpaque`; other nodes
remain opaque. Native enum/operator names render only when the selected native
contract is exact and validated; missing or mismatched contracts leave those
names absent. A `childrenLimit` diagnostic shows the bounded parent without
manufacturing descendant Event, operand, branch, or operator rows. The page
does not present condition truth, runtime variable values, handler dispatch,
cue execution, Wwise branch selection, or audibility as observed facts.

Event details include exact direct effect slots, built-in Wwise plug-in class
names, parameter fingerprints, and explicit output-bus IDs. Gain, Delay,
Compressor, Expander, three-band Parametric EQ, Meter, Matrix Reverb, Pitch
Shifter, Harmonizer, and Stereo Delay expose their exact authored base settings
from the shipped binary parameter layouts. Guitar Distortion additionally shows
all six pre/post EQ bands and its complete distortion/output control set.
RoomVerb exposes every public authoring control and the DLL's exact ER-pattern
catalog while visibly marking 11 private algorithm-tuning IDs as
meaning-unresolved. Its debug evidence also shows native use roles for five
tap-pattern inputs (endpoint pairs, seeded variation, and ER-grid
normalization), one six-channel coefficient input, and two seeded secondary
reflection-pattern inputs; three IDs remain name/read-unresolved. Convolution
Reverb shows its 13 public runtime controls and
separately lists exact impulse-response plug-in media dependencies; its two
private fields remain unnamed, while debug evidence shows the scalar forwarded
as a fifth processor float and the byte copied into runtime state; IR IDs are
never presented as playable WEM leaves. Mastering Suite definitions show their six EQ bands, four compressor
bands and crossovers, master/channel gains, and limiter settings; two private
codes and unresolved speaker names stay visibly partial. Overview and event
rows separate exact from partial semantic coverage; unsupported plug-ins would
remain visibly opaque (the current CN definition corpus has none). Audit and
Hotfix definitions stay package-scoped when numeric IDs collide. The page does
show each explicit output bus through the complete 279-definition Audio/Aux Bus
parent hierarchy. It resolves 151 non-empty bus effect arrays and 247 ordered
slots to decoded authored plug-in settings. A separate exact sibling-payload
layout join has been superseded by typed v150 `CAkBus` parsing: all 279 Bus
payloads now expose their serialized InitialFX count, with 128 explicit empty
lists and 151 non-empty lists. The same rows expose authored Bus properties,
duck records, recovery/max-duck settings, and the exact InitialFX offset. The
page does
show serialized User-Defined Aux slots through the same bus/DSP path resolver
and separately show authored Game-Defined Use/Override bits. The current
unique-node corpus contains 7,492 populated User slots targeting 25 Aux Buses,
30,162 Game-Defined Use bits, and no populated Early Reflections target. The
media shard also projects each possible decoded media leaf onto the exact
serialized Event output-bus paths that reach it, with effect-bus and
unresolved-bus IDs pointing back to the HIRC catalog. Random/switch/sequence
selection, inherited effective settings, live controls, platform DSP, and
audibility remain explicitly unresolved. Each media row also carries a compact
exact `trigger_contexts.json` `mediaRefs` join (semantic kinds, trigger roles,
owner/situation values, and selection/activation statuses); it is an authored
request/placement summary, not proof of runtime execution or branch choice.
Media rows additionally expose exact serialized Wwise media-edge types and
selection paths (`directSound`, `layerChild`, `randomAlternative`,
`switchCandidate`, sequence/music edges) plus root Action IDs. The current CN
view has 59,109 media rows with this graph evidence and 39,619 selection-path
summaries. These paths explain authored candidate construction; runtime branch
selection, caller identity, and audibility remain unresolved.
Media details also show Event-level authored context kinds, roles, owners, and
situations for the possible media set. The current CN view attaches this
summary to 44,442 media rows across 367,317 context occurrences; it is broader
than exact `mediaRefs` and is explicitly not a claim that every listed context
selected that leaf.
For 85 hash-only Events, a complete final-media leaf-set match to authored
Events also recovers a uniform broad output category (56 SFX, 21 UI, 6 voice,
2 control). This does not recover the anonymous caller, trigger, branch, or
runtime purpose.
Another 954 named Events now retain explicit category-name evidence for the
enemy, actor/UI, LevelSequence, and Gameplay-SFX naming families. Exact voice
contexts override the weak enemy-name category (602 rows) while the original
name evidence remains visible separately.
For media whose physical path is still `wwise/unknown`, the page now derives a
separate semantic category from exact evidence: 40,421 rows (34,458 SFX, 5,645
voice, 188 UI, 66 ambience, 48 control, 13 music, 3 cue). This includes 40,217
uniform related-Event joins, four exact trigger-context Event categories, and
200 exact MonoBehaviour audio-field roles. The raw physical `audioCategory` is
preserved; 276 mixed known-category joins remain unclassified. The semantic
media rows also expose searchable coarse ownership separately from category
and playback placement. Exact scene/Event/component/path joins can label a
leaf as scene environment, scene object, animation, gameplay component,
interaction, UI, voice system, or mission narration. Outdoor room tone and
authored ambient-emitter roles may recover `ambience`; generic scene emitters
retain scene ownership without being forced into an audio category.
Exact same-name AnimationClip callback evidence can similarly recover an
action SFX category. Event and media details show the matching clip, actor,
callback-derived ownership, and evidence status; partial/similar names and
clips without a supported audio callback remain unclassified.
Authored `chr_*` and `au_chr_*` Event namespaces also expose their exact
CharacterTable owner in Event/media details and search. Full internal character
keys are preferred; shortened namespaces are accepted only when their leading
four-digit id is unique in the current table. Event-leading internal tokens
such as `lastrite_*`, `lizhiyan_*`, and `pograni_*` are accepted only when the
token has one exact CharacterTable owner. Shared media shows all named
character owners, while generic character templates and concrete playback
locations remain unresolved.
All supported AnimationClip audio callbacks are shown separately from the
same-name action classification. Event/media details expose the exact clips,
callback functions, owners, reachability, and recovered AnimatorController
names even when Event and clip names differ; this relationship does not by
itself assign an SFX category or claim runtime execution.
Audio details also keep each callback Clip's resolved entity IDs separate from
candidate entity IDs. Exact Character/Enemy/EnemyTemplate overlay matches are
shown as resolved; unique-token or multi-match identities remain candidates,
and a callback used by multiple authored owners is labeled shared. Missing or
malformed overlay evidence, and unsupported Clip tokens, remain unresolved
instead of being promoted. These are static authored callback labels; Animator
execution, callback timing, Wwise branch/media selection, playback, and
audibility remain runtime-unobserved.
The semantic
index also recovers 25 unique `AU_*` field symbols whose AudioHashGenerator
hash matches a current Wwise Event (for example conveyor, laser, NPC, UI scan,
Qinshi, and mastering symbols). Event details show the declaring IL2CPP type,
field token, and exact symbol evidence; this is static symbol-to-ID identity,
not a runtime caller, trigger, branch, or audibility observation. Eighteen
Event rows now have exact current-build native trigger evidence from
`InteractiveLogicBase.SwitchAudioCustomState`, covering rotate-platform, crane,
electric-fence, ForgeIron, LifterButton, and MovingPlatform state machines.
These rows are joined to authored `InteractiveData` custom states before the
trigger catalog exposes the method/callsite, metadata usage word, and state
name. `RotateNormalStart` and `RotateOverStart` are separate branch-specific
states at one native callsite; runtime branch/execution and audible-result
boundaries remain explicit. The same fingerprint-locked catalog places the
pause/resume control Events `au_gameplay_pause_spidle` and
`au_gameplay_resume_spidle` at exact `SnapshotSystem` `PostEvent` callsites;
action-entity ownership and runtime execution remain unobserved.
Media details resolve each serialized Bus path back to the typed Bus catalog,
showing whether InitialFX is empty or populated, authored duck count/max-duck
settings, compact serialized property values, and the exact Bus
InitialRTPC-before-StateChunk suffix without inferring live DSP. All 279 Bus
suffixes parse; the current corpus contains 92 authored curves/265 points, 15
State groups, 32 States, and 34 State values. Standard controls are labeled;
out-of-range `0x1802`/`0x1804` targets are shown as custom/internal numeric
parameters rather than being assigned an unsupported DSP name.
The current-client IL2CPP metadata also cross-matches six exact game-side
GameParameter symbols to serialized HIRC IDs: `AU_RTPC_CINE_CTRL_VOL_AMB`
(`0x6b7dc358`, 3 node/4 Bus curves), `...VOL_MU` (`0x590f4cd1`, 2 Bus
curves), `...VOL_SFX` (`0x52aabb05`, 11 Bus curves),
`...IS_MUTE_BY_SDK_WEBVIEW` (`0xba4a40b7`, 1 Bus curve),
`...IS_SURROUND_CHANNELS` (`0x7ec2f9aa`, 2 Bus curves), and
`...GLOBAL_VOL_MASTER_IOS_WORKAROUND` (`0x3794392f`, 1 Bus curve). The
metadata hash and field paths are published in
`postProcessSummary.gameParameterNameEvidence`; this names game-side symbols
only and does not rename `0x1802`/`0x1804` or imply live setter state.
The same catalog is reused in Event/media RTPC and Bus-control detail rows, so
an exact game-side parameter name appears beside its serialized curve while
unmatched IDs retain the numeric/custom boundary.
Media rows with exact typed NodeBase evidence but zero serialized output-bus
nodes are labeled `noExplicitOutputBusSerialized`; the frontend does not infer
default/parent routing, silence, or an effect-free path from that absence.
When Event `postProcessSummary.effectNodes` contains direct NodeBase effect
slots, media details show a bounded separate `Direct node effects` section
(effect/plugin, node/slot, authored parameter summary, and slot flags). These
rows are exact serialized joins and do not claim live DSP execution or
audibility; output-Bus effects remain a separate section.
Media details also show a compact `Serialized effect chain` that places direct
node slots before each serialized leaf-to-root Bus path and keeps Bus slots in
their serialized order. The current CN view has 32,044 media rows with
573,360 chain stages; 64 stages are retained per row with explicit truncation.
This is an authored Event-node/Bus join for explaining post-processing, not a
claim about runtime DSP order, inherited values, branch selection, or
audibility.
The same media rows carry compact serialized Bus-control references: 31,523
rows expose 135,375 controlled-Bus occurrences, covering 332,954 RTPC curve
occurrences and 5,616 State values. Full curve points and plug-in parameters
remain in the unique Bus catalog and are resolved by Bus ID, so the media
shard does not duplicate large authored payloads.
Serialized Bus ducking is shown separately as well: 1,909 CN media rows
reach 2,249 ducking Bus definitions with 4,453 authored duck slots, including
target Bus, attenuation, fade, and target-property fields. These are possible
route records; runtime duck activation and audibility remain unresolved.
User-Defined Aux sends are also projected from exact NodeBase slots: 20,588 CN
media rows expose 27,592 unique Bus/slot targets and 698,886 underlying send
occurrences. Source node types, flags, root Actions, and target Aux Bus IDs are
kept compact; Game-Defined IDs and live send levels remain runtime-only.
Each target also retains its exact serialized Aux Bus parent path and effect-Bus
IDs, so the possible send route can be followed into the typed Bus/DSP catalog.
Serialized NodeBase properties and ranges are also summarized per possible
media path: 53,882 media rows expose 715,175 distinct authored property
signatures across 18,436,139 occurrences, while 21,526 rows expose 48,721
range signatures across 113,639 occurrences. The media view is compact; raw
U32 forms and complete node provenance remain in Event evidence.
Media details also show bounded exact `Serialized RTPC controls` and
`Serialized State overrides` sections joined from the possible Event path. The
current CN view has 4,300 media rows with 20,254 RTPC control summaries and
1,292 rows with 2,339 State-value overrides; each curve keeps at most eight
points and marks truncation. These rows explain authored control shape only,
not live setter values, selected branches, inherited properties, platform DSP,
or audibility.
Game-Defined Bus IDs, listeners, and control values are runtime assignments,
so the page does not invent those wet paths or present effective inheritance
and live bypass/RTPC/State controls as observed runtime state. Event details
also show exact authored StateChunk overrides and InitialRTPC curves, including
control type, property, accumulation/scaling, and every response point. The
current generated view contains 1,784 State Group references, 1,640 State
property values, and 19,001 RTPC curves with 67,327 points. Existing exact
control evidence labels the gamepad backend's XInput/ScePad values and known
`au_rtpc_*` hashes; unresolved IDs remain numeric, and no row claims the live
control value, selected backend, inherited effective property, or audible
result. Event cards also show 90,639 traversed nodes with 165,161 authored
AkPropID base values and 1,650 ranges, retaining each raw U32 and finite-float
form while typed ID/integer unions remain integer-labelled. The current corpus has no initial BypassFX/BypassAllFX property IDs, so
direct bypass flags and dynamic bypass remain distinct unresolved boundaries.
FX slots also annotate authored bypass/ShareSet/rendered bits without treating
them as proof of runtime DSP execution or audibility.
Event rows also show exact non-playback Action payloads recovered from the v150
bank: SetState/SetSwitch IDs, GameParameter value ranges and fade policy,
Stop/Pause/Resume flags, Seek, value/filter actions, exception buses, and FX
slot bypass controls. The current named-event corpus has 6,735 typed control
actions (including 3,455 State and 304 Switch triggers); these rows describe
authored dispatch intent only, never live state, selected branch, effective
inheritance, DSP execution, or audibility. Unsupported tails remain visibly
fail-closed with their offset/reason. The current selector catalog joins 1,601
Action group references and 1,042 exact value references, covering three
native-backed selector roles plus ten current-metadata music State groups.
Typed type-6 package branches use the same catalog (for example XInput/ScePad
and music enum members); IDs remain hexadecimal when no exact value name is
available.
The projection also shows 12 same-event Set/ResetGameParameter → InitialRTPC
exact-ID joins (2 unique IDs) as authored curve targets. Parameter names, live
values, effective DSP, and audibility remain unresolved.
The control catalog also publishes five exact metadata-named InitialRTPC
parameters covering 14 curve occurrences across six Event occurrences, with
trigger contexts, controlled properties, response-point totals, and
interpolation labels.
The schema-117 Audio index also exposes
`controlCatalog.staticRtpcAlignment`: its six canonical `AU_RTPC_*` names are
joined to exact numeric HIRC IDs, serialized curve/property evidence, and
same-event Set/ResetGameParameter controls. These rows are labeled authored
static evidence; runtime parameter values, setter execution, target objects,
branch selection, DSP state, and audibility are not rendered as observed
facts. If the selected `global-metadata.dat` + `GameAssembly.dll` gate or the
serialized source contract is missing, mismatched, malformed, or stale, the
static names/rows fail closed and the Audio page keeps the diagnostic instead
of showing stale identities. The generated page data appears after a formal
semantic rebuild.

When native inputs are missing or mismatched, authored Audio rows remain
visible; only build-locked callsites, mappings, and addresses disappear, with
the unavailable state shown explicitly.

Shared SFX/music and language voice stay in separate storage roots. Repeated
media IDs preserve every physical occurrence and package provenance. Direct
Story-line binding, authored context, Event-only relation, and unknown placement
are mutually exclusive generated media states.

The default purpose-priority sort and recovery filters put unknown-purpose
Events/media ahead of partial and known-purpose records. A direct Story-line
binding is a terminal known-purpose state and is not part of the investigation
queue. Candidate player cards stay expanded and materialized unless more than
20 candidates share the same playback group; larger groups start collapsed.
On a selected Audio record, the playable-media block appears immediately below
the detail heading, before the longer facts and evidence sections.
Responsive enemy-voice contexts may show the fingerprint-locked
`EnemyTriggerVoiceAction` voice-type-to-trigger-key mapping, while live branch
selection and audibility remain unobserved.

## Mission Pipeline

Mission Pipeline shows evidence-typed trigger chains and the gaps between
Story definitions, mission ownership, activation, and playback.

- Native registration or code-address order never implies mission order.
- Definition-only rows remain distinct from activation evidence.
- Unlinked native playback keeps an explicit ownership gap.
- Unlinked native playback rows show per-Story active-overlay trigger
  confirmation, including decoded slot/shape and source hash for spatial
  volumes or the exact event carrier for non-spatial triggers. This is local
  context only, not proof of ownership, firing, branch choice, or order.
- The Mission Pipeline spatial map draws exact authored trigger volumes from
  decoded X/Z position, size/radius, and rotation. Exact non-spatial event
  carriers and files with no trigger lead remain separate named lists.
- Strong and weak graph edges remain visually and semantically separate.
- Manual/OCR order may guide research but does not upgrade source evidence.

## Map recovery

The debug-only Map Recovery page projects exact authored world-space evidence
onto X/Z and keeps a rendered scene background optional. Marker coordinates and
render bounds must share the same declared world-coordinate transform; an image
that lacks auditable bounds is not evidence of placement.

Every level is recovered by the same code path, with no level id written into
the builder. `WorldEntityRegistry` keys its world entities, script entities and
NPC proxies by a global id whose leading digits are the level's own `idNum` from
`LevelBasicInfoTable` (`idNum = id // 10**8`), so a level's plottable entities
select themselves: `indie_dg002` is `idNum 87` and owns ids from `8700000000`,
`indie_dg004` is `idNum 239` and owns ids from `23900000000`. A level is
published when it owns at least one plotted node; an id whose `idNum` no level
row declares is dropped rather than guessed at, because it has no coordinate
space to sit in. The map selector groups the published levels by family -
map01 is 四号谷地 (Valley-IV) and map02 is 武陵 (Wuling), named by the levels'
own recovered display names - and labels each level with the name the builder
resolved from `LevelDescTable` plus the per-language `I18nTextTable` (empty or
placeholder texts keep the bare level id) alongside its node and story counts.

Levels in one region share a single world-space canvas, but remain separate
selectable sub-maps. `UILevelMapLoadConfig` supplies the exact chunk rectangles,
optional tier overlays, and the only supported orientation flag
(`needInverseXZ`); exported tile rows are not flipped independently. Multi-tier
regions start with the selected sub-map's first tier visible. A current-floor
slider on the lower-left map surface groups every rendered sibling overlay in
the stitched region and switches one floor at a time, with an explicit base-map
position, so transparent floors from different heights never blend. It is
hidden when no tier image was actually recovered; the same light control dock
retains the pan/zoom keyboard and wheel hints without a separate floating hint.
Geographic
`regiontoast` overlays use their recovered place names; only authored
`layer_tips` keys are presented as numbered floors. Numbered floors sort in
ascending order before the remaining tier-id-ordered geographic overlays.
Tier chunk rows retain the exported top-to-bottom, +Z-at-top orientation just
like base-map chunks; `needInverseXZ` changes world-pin projection and never
rotates the exported composite.
Registry markers, quest points, and authored
`staticElements` all retain raw X/Z coordinates; marker-to-tier membership is
published only when the point lies inside that tier's authored rectangle.
The level display name identifies a gameplay scene, not ownership of every
pixel in its overlapping map-screen rectangle. Region stitching therefore
uses a stable background order, and geographic labels are positioned from the
localized `UILevelMapLoadConfig.staticElements` text anchors. Selecting a
different sibling level must not reorder the region surfaces or make named
places appear to exchange positions.

Only the Map01 and Map02 families are stitched into regional canvases. Other
same-prefix levels can be separate states or decks with identical bounds; the
two Dijiang maps therefore load independently. Their composites retain the
exported orientation shown by the in-game reference (prow/bridge left and base
area right), while `needInverseXZ` converts world pins with the evidenced
clockwise quarter turn `X'=Z, Z'=-X`. This applies identically to markers,
routes, and location labels. Where game minimap art is absent, a
recovered HLOD surface is preferred; otherwise the page uses an explicitly
evidence-only, height-tinted point cloud made from exact registry and quest
X/Y/Z transforms without inventing terrain. The expandable mission list links
the files owned by each mission. Selecting one mission shows all of its plotted
markers across ordinary marker and floor filters, focuses their footprint, and
the map can be zoomed to 48x for close inspection.
The selector orders Dijiang first, then Valley-IV, Wuling, and finally dungeon
and independent-scene families.
Map feature scripts, styles, and regenerated background images carry the same
release cache key so an ordinary page reload cannot mix an old coordinate
projection with a newly generated minimap composite.

Both marker points and background rectangles use the same `screenY = maxZ -
worldZ` projection. Do not place a background with `worldZ - minZ`: that
mirrors every stitched screen north/south while leaving task coordinates in
the original orientation, producing apparently mismatched edges and pins.
Opening any `map01` or `map02` level loads every sibling background in that
region immediately; readers do not need to change the selector once to finish
the stitch. Selecting a sub-map automatically frames its own map-screen extent,
including in the clean view where no entity nodes are enabled. Source minimap
alpha is rendered directly without an additional whole-image opacity, avoiding
artificial dark seams where sibling screens overlap. The initial view is a clean
geographic map with no quest/entity overlay selected, and an available stitched
surface is not reported as an empty node layer. One primary place label per sibling remains visible,
collision-free local names appear progressively with zoom, and quests, dialog
markers, or other entity layers are explicit user choices.
The pan surface suppresses native text/SVG selection from pointer-down through
drag completion, including when pointer capture carries the drag outside the
map, so panning never highlights labels or surrounding interface text.
The map canvas uses a subdued dark stripe outside recovered textures. The
lower-left floor control and help text reserve the default controls-panel width
instead of sitting underneath that floating panel.

Because one level hosts many missions and one mission can reach several levels,
every contribution is gated on the coordinate space it names: mission-area
proximity rows on their `pin.mapId`, authored map pins on their own `scene`
field, and quest centroids on `questSpatialTrack.scenes`. A quest whose tracked
pins span two levels has a centroid averaged over two unrelated coordinate
spaces, so it is plotted on neither map rather than at a position that exists in
neither.

Every plotted node publishes a `relatedFiles` list, and the page's right-hand
inspector reads those files in place: dialog and text payloads render as
speech, `LevelScriptData` blobs render as their embedded identifier strings,
and anything else renders as truncated raw text. Each pin declares the link
that produced it, and `strength` separates the two evidence bands the page
keeps visually apart:

- `strong` - an identity match. `story_exact_producer` (registry-backed
  script/slot producer), `story_npc_proxy` (a scene bound to a named NPC proxy
  the registry places exactly), `story_script_slot`, `story_map_pin`,
  `placement_source`, `mission_area_definition`, `level_script`,
  `mission_runtime`, `entity_registry`.
- `weak` - diagnostic or scoped context. `story_proximity` (a scene placed
  near the node), `story_quest_anchor`, `story_script_condition`,
  `story_script_reference`, `story_anchor_script`,
  `story_mission_area_candidate`, `story_mission_scope`, `story_source`,
  `mission_reference`, `level_definition`.

Story files reach the map through five independent bindings:

| Source | Binding | Strength |
| --- | --- | --- |
| `flow.missionStoryConnections` | producer script/slot, exact when the registry resolves the entity | strong when exact |
| `timelineRecovery.npcProxyDialogAttachments` | scene to `npcProxyId`, joined to the registry's `npcProxyBriefInfos` transform | strong |
| `flow.mapPins` | authored pin with an exact position, the quests it serves, and the NPC proxy it follows | strong |
| `timelineRecovery.scriptConditionAttachments` | scene play condition to a level script in a named map, with no slot | weak |
| `levelscriptSpatialProximity` / `questSpatialTrack` | mission-area trigger volumes and quest centroids | weak |

Markers carry a structural `kind` (`story`, `narrative`, `npc`, `trigger`,
`travel`, `device`, `collectible`, `scenery`, `enemy`, `spawn`, `waypoint`)
classified from `detailId` and, failing that, from the registry's own
`entityType`. `kind` is never upgraded because dialog happens to be pinned to a
node; `storyCount` reports that separately, and the page draws its story ring
from `storyCount`, so the story layer is exactly the set of nodes with a dialog
to open.

A node placed by the registry sets `registryBacked` instead of repeating one
identical level-wide 7 MB registry path on every marker; the inspector rebuilds
that pin from the map's own `relatedFiles` entry. On the largest map this is
about a megabyte of pure repetition.

A named slot is a gate, not a hint. Once a connection resolves the entity slot
its story is produced from, that story is pinned to that slot only - never to
the script's other slots, and never to its listener or ordering-anchor scripts,
whose identically numbered slots are unrelated entities. `anchorScriptIds`
order a scene rather than play it, so they carry their own `story_anchor_script`
relation and only apply when nothing else resolved.

`triggerSlotIds` (from `ScriptEvent_OnLeaderEnterTriggerVolume`) are numbered in
a level-script-local space that shares no id with the WorldEntityRegistry
script/slot space, so they cannot be placed. They are published as
`unresolvedTriggerSlots` and shown in the rail, which keeps a story's
mission-area pins from reading as its recovered trigger position.

Spatial proximity rows reach the map through two different doors. A row pinned
to a mission area becomes a trigger marker; a row pinned to a `trackingPos`
has no area to become, but still names a quest, so it is pinned to that quest
point. Consuming only the first kind silently dropped five scenes and two
level scripts from the payload.

### Why a mission story can be absent from the map

A scene reaches a plotted node only through a spatial anchor. `unplacedStories`
names every mission scene that has none, grouped by reason, and the rail links
each one into the Story view:

| Reason | Meaning |
| --- | --- |
| `mission_scope_only` | scoped to the mission's whole area set; reachable under map-wide files, but not placed |
| `cross_level_binding` | driven from another level's `sceneBindings` chain (those scenes are placed on that level's own map instead) |
| `graph_evidence_only` | scene-to-scene ordering edges only, with no area, producer entity or proximity row |
| `no_placement_evidence` | no spatial evidence of any kind in the mission payload |

This is an evidence boundary, not a gap in the linker: an unplaced scene carries
no coordinate anywhere in the exported data. Counts per level are in the
generated payloads and in the page rail, not repeated here.

Every pinned dialog file also carries a Story deep link
(`?lang=<LANG>&ui=<locale>&story=<key>#story`), so a marker's text can be read
in place on the map or opened in the Story view with its full line order,
options and audio. The data language is read back from the pin's own path.

A story whose mission-area set covers every area of the mission says nothing
about any single trigger, so it is pinned map-wide (`story_mission_scope`)
instead of being repeated on each trigger. `unlinkedMissionFiles` therefore
lists only the mission-referenced files that no plotted node claims at all.
`linkedMissionFiles` keeps its narrower original meaning: files that prove a
marker's placement.

`build_map_recovery_data.py` rebuilds every level in one pass, reading each
mission payload once and reducing it to a compact per-level digest so the whole
mission corpus is never resident at once. Pass `--level` (repeatable) to rebuild
a single map while iterating.

### Filtering a map

A world map pools every mission that plays in the level, so the page filters on
two independent axes and publishes the counts each one needs in the payload's
`facets` block.

- **Mission.** The selector isolates one mission at a time, ordered by how much
  of the map each accounts for. A node is claimed by a mission only when that
  mission authored the dialog pinned to it, when the node is that mission's own
  map pin or trigger area, or when it is one of its quest points; story rows
  carry their owning mission for exactly this reason. Registry entities with no
  dialog are level art and belong to no mission, so they appear only under
  "All missions" rather than being attributed to whichever mission is selected.
- **Layers.** `kind` is the top level and `subKind` the second, because
  `collectible` is not one thing: chests, ore nodes and currency pickups are
  separate questions. A kind with a single subKind stays a plain row. `All`,
  `None` and `With dialog` reset the tree; the last keeps only kinds that
  actually carry recovered dialog. Each row shows its node count and, in the
  story colour, how many of those nodes have dialog attached.

Counts come from `facets`, not from a node scan, so a hidden layer still reports
how much it is hiding, and a filtered map shows a `shown by filters` metric
beside the unchanging level totals. Filter changes coalesce into a single render
(via a timer, not `requestAnimationFrame`, which does not fire in a hidden tab),
because re-plotting a full map is a few hundred milliseconds of SVG layout and
the two-level tree invites several clicks in a row.

Initial activation fetches only the selected level and starts with
dialog-bearing markers rather than every entity. Selecting another level is the
explicit request to fetch and merge that region's siblings; the shared loader,
busy state and inline retry match the other lazy WebUI views. `All`, `None` and
`With dialog` remain explicit display choices after loading.

### Lines on the map

Two kinds of line are drawn, and they mean different things.

**Quest routes** are one polyline per mission, through that mission's quest
points in its authored `questOrder`. Both parts matter: a single polyline over
every quest point on the map drew a false leg from the last quest of one mission
to the first of the next, and ordering by `questId` sorts lexicographically, so
`q#10` landed between `q#1` and `q#2`. Every published quest point carries a
numeric `questOrder`, which is the authored sequence.

**Relation lines** join two markers that share a level-script file or a script
entity. This is a clique: every pair in a group is joined, so a group of n draws
n(n-1)/2 lines that all carry the same one fact. They are also a file-level
co-occurrence, not a spatial or narrative link - one script can own entities
scattered across the level, so a long line between distant markers says only
"same file". They are therefore focused by default: only the lines of the node
under the pointer, or of a pinned node, are shown. `All` and `Off` are available
in the rail. Visibility is switched by rewriting a single stylesheet rule rather
than touching each line, so focus can follow the pointer on a map with thousands
of nodes. Groups larger than 24 members are dropped entirely rather than
thinned, because a partial clique would misrepresent which members are related.

### Background renders

The preferred background is the game's own map screen: `build_map_recovery_data.py`
composites the level's medium-LOD chunk textures (exported under
`convert_by_type/Texture2D`) onto the exact world rectangles
`UILevelMapLoadConfig` declares for each chunk, with the image top on +Z like
every marker projection. A chunk grid with a hole, a missing chunk texture or
a degenerate scale fails closed to the high/low LOD and finally to the HLOD
preview; whichever source wins also supplies the declared `worldBounds` the
markers stretch against, and the rail states which one the page is showing.
Each chunk draws at its own world size (half-size cells included), and a
sidecar records the chosen textures by hash so an unchanged rebuild reuses the
published composite instead of repainting it. `basic.needInverseXZ` is recorded
as a pin-projection contract; it does not rotate the chunk composite.

The page fits a single on-demand zone to its own declared rectangle. After the
reader requests a sibling, the generated `region.worldBounds` union becomes the
one full-viewport transform for every loaded zone of the same region (map01,
map02, base01, ...), so
the overlapping zone map screens tile into one seamless surface with no
outline between zones; the selected zone draws last, on top of its
neighbours. Markers, routes and every zone picture share the fitted
rectangle. This fixes the former use of only the selected zone's bounds, which
clipped or displaced sibling screens in Wuling and Valley-IV. Pan/zoom runs over
the loaded region (the pan limit follows the
plotted content, not the canvas edge), and fit/reset operate on the region's
plotted nodes and union bounds. All page chrome - title and
metrics, map/mission/layer controls and the inspector - is a floating panel
that drags by its header and collapses onto it.

Every level with HLOD art also gets the diagnostic top-down backdrop, built by
`build_map_recovery_preview.py` from the AnimeStudio AssetMap and exported OBJ
meshes. It is the fallback background wherever the in-game map screen is not
available; a level with neither publishes markers on marker-derived bounds and
says so in the rail.

The HLOD bundles publish `Mesh`, `Material` and `Texture2D` only - no
`GameObject` or `Transform` record survives the export - so a cluster's world
placement cannot be read out. It is inferred from the cluster name
(`S_HLOD<lod>_<i>_<j>_Cluster_<hash>`), whose grid index is the only spatial
hint, plus two quantities that are recovered rather than assumed:

- **Cell size.** It doubles per LOD and `HLOD0` is 64 m. The independent check
  is `indie_dg002`, whose 128 m `HLOD1` cell was derived by hand before this
  builder existed and which the general rule reproduces exactly.
- **Grid origin.** Fitted per level by asking which origin makes that level's
  own exact marker transforms land on cells that actually carry geometry, at
  every LOD at once. The fit is corroborated across levels rather than tuned:
  one shared power-of-two-aligned origin (`-1024`) explains `indie_dg002` and
  every `map01_*` level, and another (`-2048`) explains almost every `map02_*`
  level - agreement a per-level curve fit would not produce.

Origins are still fitted per level and never forced to the family constant.
`map02_lv005` is the reason: its own markers score 93% at `(-2048, -1920)` and
only 59% at the family `(-2048, -2048)`, so levels demonstrably do carry their
own origin.

Every manifest publishes the fit that produced it - `coverage`, `bestCoverage`,
`samplePoints`, `tiedOrigins`, `alignmentBits` - and the page prints coverage
and origin in the rail, so a weak background reads as weak. A level whose origin
is under-determined (fewer than 50 marker transforms, or under 90% coverage)
publishes no background at all rather than a plausible-looking guess.

The image uses the earlier dense 3D scan/point-cloud presentation:

1. **Depth pass.** Every cluster triangle is rasterised orthographically from
   directly above with a depth test on world Y, giving a digital elevation
   model of the level.
2. **Density sample.** A deterministic screen-door sample keeps roughly 73% of
   pixels hit by real HLOD triangles, preserving structure while exposing the
   background between points.
3. **Elevation tint.** Exact depth values tint the recovered points from cool
   blue-grey to warm ivory, retaining readable vertical relief.

The renderer deliberately adds neither mesh-normal lighting nor grown terrain.
Every visible point comes from a real triangle depth hit; gaps remain missing
evidence instead of being joined into a plausible-looking solid surface.

Bounds are the marker bounds padded to the page's viewBox aspect, so the image
is not stretched against the markers drawn over it, and the PNG is ink on
transparency so it inherits the page's own surface.

Two limits are worth stating plainly, because both are data ceilings rather
than rendering choices:

- **No textures.** The HLOD containers publish `Mesh`, `Material` and
  `Texture2D` (15,338 albedo/normal PNGs are exported), but the mesh, material
  and texture hashes are all different and no `Renderer` binding survives the
  export, so no mesh can be joined to its material. The surface is shaded, never
  textured, and the exported HLOD textures are unusable until that binding is
  recovered.
- **No ground.** `realPixelRatio` runs from about 12% to 77% per level. The
  uncovered pixels are not open ground: for these scenes HLOD publishes cliffs,
  props and structures but no ground surface, and no `TerrainData` or other mesh
  exists in the art scene either. Everything beyond recovered triangle hits is
  left empty, because a gap is missing data and an invented floor would imply
  coverage the export does not have.

These remain diagnostic previews labeled `inferred_hlod_grid_preview`, useful
for checking route alignment and scene coverage. They are not exact scene
transforms or textured map renders.

For a level with no usable map-screen texture, the preview manifest also
publishes a bounded `modelScene` subset of the same exported HLOD OBJ meshes.
The evidence panel links those meshes into the existing Assets 3D viewer. Paths
must remain under `export_full`; publication fails closed above 24 meshes or
120,000 triangles and states marker-only fallback when no safe model survives.
The grid translation and Unity-to-OBJ axis conversion remain explicitly
inferred, not exact scene hierarchy evidence.

When a level has no HLOD cluster container but exported OBJ filenames contain
that exact level id (for example a base01 deck), the map payload publishes an
asset-only `modelScene` with `positionStatus: unplaced`. Those links open the
existing Assets viewer but never become map geometry or a background; shared
family names such as `base01` are not used to assign an OBJ to every deck.

The builders read each other's output, so a full rebuild runs data, then
previews, then data again to embed the new manifests:

```bat
python scriptsuild_map_recovery_data.py
python scriptsuild_map_recovery_preview.py
python scriptsuild_map_recovery_data.py
python scriptsuild_map_recovery_preview.py --level indie_dg002
```

`build_map_recovery_preview.py` scans the 750 MB AssetMap once and caches the
per-level HLOD grid index at `reports/assets/map_recovery/hlod_grid_index.json`,
keyed by the AssetMap hash; pass `--refresh-index` to force a rescan.
`audit_map_asset_closure.py` remains available for one-off needle audits of a
single map's asset closure.

### Sub-levels with no mission of their own

A level that hosts no mission still gets a map when another mission's authored
chain runs inside it. `indie_dg004` is the worked example: `LevelBasicInfoTable`
declares it with `idNum 239`, two missions (`e0m0` and `e4m1d5`) host sub-level
data there, and neither declares it as its own `levelId`, so it is a secondary
level both missions teleport into rather than a region of either one's map.

Its recovered surface is four exact transforms: three WorldEntityRegistry script
entities (`int_narrative_empty` narrative anchors) and the arrival point of
`TpForLs_23900030000_0c8be1bb` from `LevelScriptTeleportValidationDataTable`.
Everything sits within ~15 m of the level origin, against X -384..512 /
Z -192..960 for e0m0's content in `indie_dg002` - the two coordinate spaces have
nothing to do with each other, which is why a quest centroid is never carried
across a level boundary.

The payoff is that `cutscene_e0m0_6/7/8`, which the `indie_dg002` map has to
report as `cross_level_binding`, are pinned here on the anchors of the script
that plays them. Their `sceneBindings` chains name a level-script file but never
an entity slot, so they attach at slot-less strength rather than being claimed
as exact placements.

`tools/Endfield-map-extractor/` is an optional research reference rather than a
WebUI dependency. At inspected commit `956596b48ff04451fc0223021d7af284f2c64cda`,
its `EndfieldSceneProbe` can inventory GameObject/Transform hierarchies and the
Renderer-to-Mesh/Material/Texture dependency closure, and export referenced OBJ
meshes. That is a promising route to an orthographic background after a small,
audited physical-bundle closure has been selected.

Do not treat the optional extractor's output as an e0m0 map. Its public extraction profiles,
terrain/instance paths, and Blender bounds are specialized to Map01/Map02; the
public job path emits audited data packages while Blender build status remains
`not_ready`. A future exact e0m0 pass must add an `indie_dg002` profile, recover
the scene Transform closure, and replace or validate the inferred grid formula
before upgrading the current diagnostic background.
The checkout is ignored under `tools/`, expects a game root containing
`Endfield.exe` rather than `Endfield_Data`, and uses the PolyForm Noncommercial
1.0.0 license; review that license before copying implementation code.

## Updates

Updates displays changes produced by comparing two complete export roots. The
default feed covers WebUI-facing exported text plus image, model, video, and
decoded audio assets. It must never treat changes under `webui/`, `reports/`,
`memory/`, or `scratch/` as game-data updates.

```bat
.\build_updates.bat OLD NEW
```

## Build and verification

Use the smallest relevant root workflow:

```bat
.\export.bat
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
.\export_assets.bat
python scripts\pack_webui.py
```

Before reading an existing extraction, run
`python scripts\verify_export_freshness.py` unless freshness is already known.
If it is stale, refresh with `.\export.bat --from-game`.

After frontend or generated-data changes:

1. Load every normal page and check the browser console.
2. Toggle debug mode and verify Mission Pipeline routing in both directions.
3. Check Story reset, recovery filters, and SNS emoji/sticker fixtures.
4. Open a playable character and enemy; verify variants, progression, skills,
   projectiles, sounds, and asset links.
5. Confirm unavailable optional inputs produce a clear degraded state.

Useful Story media fixtures are `test_sns_emojicomment`, `test_sns_sticker`,
and `sns_topic_map02_lv005_12002`.
