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
