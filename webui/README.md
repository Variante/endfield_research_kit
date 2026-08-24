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
| Map | Authored world-space evidence with minimap, model, point, and water layers |
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
- `src/features/map_recovery/`: normal Map view immediately after Story, with a full-bleed world surface, a three-column map/task/object-filter tree, a detailed JSON/file inspector, stitched config-proven regions, authored quest routes, and evidence-linked markers. Unnamed single-mission maps use the localized mission code/name; authored cross-map Story continuations are explicit navigation links.
  Current-build validated local Story trigger volumes are drawn from their
  decoded Box/Sphere geometry at authored X/Z position and rotation. Their
  Story links remain distinct from nominal mission context and do not imply
  mission ownership or runtime firing. Current-build native consumers confirm
  that these ids address the LevelScript-local `triggerVolumes` domain through
  a runtime registered-id bridge; they are not WorldEntityRegistry slots.
  MissionArea pins draw their exact MissionAreaTable Box/Sphere definition but
  remain Story-unresolved. Spatial proximity never supplies their Story files
  or Story order.
  Selecting a mission keeps missionless level-world entities available through
  the ordinary type/floor filters; compact maps enable all recovered object
  types by default. Enemy, device, scenery, and travel markers use distinct
  glyphs, and authored grenade towers retain their Factory/Combat/Model evidence.
  Enemy labels resolve through EnemyTemplateDisplayInfo plus localized text;
  exact reading points use the generated Story title instead of their internal
  `text_*` key. Empty `int_empty` shells live in their own unresolved-empty-slot
  layer, disabled by default, rather than being presented as understood
  interactions. A registered shell referenced by a strict constant
  `Param<EntityPtr>` value inside a validated action record moves to a separate
  script-target layer only when a build-locked native formatter contract also
  proves its named member boundary; unresolved occurrences remain in the
  default-hidden candidate layer. Neither form inherits sibling Story,
  cutscene, or sequence ownership. Script-container files,
  conditions, and ordering anchors stay map-level context: they are not repeated
  on every sibling slot. A point receives a Story or file only from an exact
  script/slot consumer. Opening `WorldEntityRegistry.json` from a registry-backed
  point resolves its exact world id or script-id/slot pair, jumps to the matched
  row (and paired brief-info array index), and highlights the focused excerpt.
  Every spatial world/script registry slot publishes an observational action
  binding status and an action array. `no_reference_observed` means only that
  current decoded LevelScript evidence contains no matching constant pointer;
  it is not proof that the slot has no action. Exact and unresolved references
  remain separate when both address the same slot. Full builds also write the
  exhaustive audit to `reports/assets/map_recovery/action_binding_index.json`,
  including every contracted EntityPtr field state, diagnostic-only dynamic
  `idRef`/output/variable references, and non-spatial references that must not
  become map markers. A dynamic local-output reference becomes a slot action
  only when a pinned producer contract proves a same-header constant alias;
  validated non-alias outputs remain unplaced.
  NPC proxy rows use their own identity domain. Build-locked `NpcProxyGetter`
  references can attach actions through an exact proxy-id/segment/table join;
  they never reuse a numerically equal world-entity identity.
  Current-script slot actions use a pinned native resolver contract: the
  runtime lookup is keyed by the current LevelScriptRuntime script id and slot
  in EntityManager. A unique WorldEntityRegistry script/slot row proves the
  authored map target, while runtime registration and lifetime remain explicitly
  unproven.
  World scenery also receives Story links when one counted LevelInteractiveData
  record stores both its exact `embeddedLogicId` and NarrativeComponent
  `typeId`; e0m0's four tombs use this direct binding rather than numeric order
  or spatial proximity.
  When a map node has a generated Story conversation, its inspector shows that
  conversation as the normal reader-facing file and keeps placement, registry,
  script, and other evidence files behind `Show debug info`.

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
- All search boxes accept case-insensitive regular expressions. Queries are
  split on whitespace with OR semantics, so `^npc_`, `boss|elite`, and `map0[12]`
  are useful examples; malformed expressions are treated as literal text.
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
- Cutscene rows can show an automatic `未使用` badge only when the current
  build's complete, non-degraded playback-carrier census finds no exact or
  uniquely case-insensitive consumer. Case collisions and incomplete scans
  remain unresolved and unmarked. This evidence badge is separate from the
  user-managed `possiblyUnused` Story-order override.
- `overrides/options.json` stores manual option placement/response recovery.
  Story keeps the generated option-evidence issue and its count unchanged;
  manual coverage adds a separate filterable override tag instead of replacing
  source-state classifications such as unregistered table-only placement.
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

When a verified offline audio capture bundle is supplied to the semantic
publisher, Event details show the observed managed request boundary and media
details show the exact related Event/session. Missing, mismatched, or
unverified bundles remain degraded diagnostics and add no runtime bindings.
Observed request evidence still does not claim Wwise branch selection,
decoded-media selection, or audibility.

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
Event cards and search expose compact scene-emitter containment and prefab
identity status sets. The current prefab-local result is labeled as a static
authored emitter with scene unresolved and prefab identity unavailable; it is
not an exact context tag. Scene IDs appear only for exact SceneAsset/Level
containment or exact prefab Source+PathID evidence joined to one level.
Candidate paths, sidecar level IDs, names, positions, and mixed exact rows
remain diagnostic-only.
If explicit component identity and exact prefab-path identity disagree, the
page keeps the join unavailable with `conflictingPrefabInstanceIdentityJoins`
instead of choosing one route.
Scene-global Event cards and details expose exact authored scene IDs and the
original serialized semantic roles only when every direct context validates
against the merged scene catalog. The context filter and search use the same
exact/unavailable contract; partial, malformed, non-direct, truncated, or
out-of-catalog rows remain diagnostic-only and never alter category, Wwise
resolution, runtime, branch, playback, or audibility state.

Streaming-instance rows expose their exact entity/name/transform and bounded
raw ECS evidence separately from prefab identity. The current validated
InitChunkData schema has no known prefab Source+PathID/hash field, so the Audio
page leaves level ownership unresolved unless a future exact numeric identity
resolves to one unique full AssetMap container path or explicit component
identity. Basenames, names, positions, Meshes, and similarity are never search
or ownership evidence; StreamingChunkData correlation remains an explicit gap.

RemoteCommon `startAudioEvent`/`endAudioEvent` lifecycle fields are shown as
separate authored trigger contexts after the exact Persistent-over-Streaming
row overlay; runtime execution and playable-media selection remain separate.

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
The Audio overview loads `data/lang/<LANG>/audio/scene_backgrounds.json` as a
compact scene catalog. It reports validated and missing object-index sources,
keeps partial coverage visible, and lets users filter scenes by scene id,
mission id, or Event. Event chips navigate to the existing Audio Event detail;
the catalog does not duplicate Wwise branches or media. AudioLevel rows and
mission-to-scene references are authored static evidence. Prefab-local
emitters stay visibly unresolved to a level, and the page does not claim
runtime scene activation, Event posting, branch selection, or audibility.
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
Gameplay character items also expose these exact namespace-owned Events and
their playable candidates in a separate collapsed group. They are not merged
with skill or animation-triggered SFX: the group is identity-only and does not
claim an action, skill, Event post, selected Wwise branch, or playback.
Enemy items expose a parallel collapsed group for recovered `au_` Event names
whose complete prefix exactly matches one current EnemyTable id. These rows
remain separate from enemy skill and animation audio because the names come
from bounded grammar/hash recovery rather than a recovered consumer.
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
When the callback token has one agreeing `NpcInfoTable` plus
`NpcTemplateGroupTable` owner and one exact `AudioDialogChannel` key, details and
search expose the NPC id, template, and actor token as `ownerKind=npc`.
Duplicate/generic tokens, missing channel identity, overlay conflicts,
malformed rows, and template mismatches stay unresolved. Mixed Events retain
the NPC only on occurrence/Clip evidence and do not receive a single NPC owner.
The semantic
index also recovers 25 unique `AU_*` field symbols whose AudioHashGenerator
hash matches a current Wwise Event (for example conveyor, laser, NPC, UI scan,
Qinshi, and mastering symbols). Event details show the declaring IL2CPP type,
field token, and exact symbol evidence; this is static symbol-to-ID identity,
not a runtime caller, trigger, branch, or audibility observation.
Events whose name no shipped string reaches are named separately by
grammar-directed preimage search: head/tail name templates mined from proven
names regenerate sibling spellings, and a candidate is kept when its
AudioHashGenerator hash equals a current hash-only Event id. Such a name is
shown with `eventIdentityStatus=grammarHashPreimageNameRecovered`,
`eventNameSourceKind=grammarHashPreimage`, and the head/tail sibling counts
that admitted it, so it reads as a weaker name source than a shipped literal.
Names with two spellings for one hash, or with no sibling recurrence at a
shared split boundary, are never promoted to an Event name. The recovered
spelling supplies the owner and category it encodes and no caller, trigger,
execution, branch, or audibility. Eighteen
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

## Map

Map is a normal page immediately after Story. It plots authored Unity X/Z
coordinates and only draws a background when the image and its world bounds
share an explicit transform.

Current generated contract:

- `data/map_recovery/index.json` lists maps, their exact `regionKey`, the
  current default map, and compact counts.
- `data/map_recovery/maps/<levelId>.json` owns markers, quest points, facets,
  mission/file evidence, minimap metadata, and one recovered render manifest.
- `data/map_recovery/render/` owns generated minimap composites, elevation,
  surface, point, height-mask, and water PNGs plus their manifests.
- Shared-scene identity comes only from the directly addressed
  `LevelConfig/<levelId>.json` streaming path. Similar names are not evidence.
- Streaming-instance sidecars use schema 2 and one `meshes` array per entity
  base. They feed static render layers only and are not duplicated as clickable
  map nodes.
- Every point layer owns its height mask as
  `pointCloudOverlay.heightMask`; there is no top-level mask fallback.
- The browser derives stitched bounds from the loaded background rectangles;
  region bounds are not duplicated in index or payload metadata.

Frontend behavior:

- A map opens as clean geography. The resizable left panel is a three-column
  map/task/object-filter tree; map status is kept with the task column instead of occupying
  a separate header panel. The complete JSON/file inspector is also resizable.
- Physical level variants that share one authored place are one map entry and
  remain selectable as map items in the task column. Their per-level payloads
  and inspector JSON are retained; only the duplicate navigation entry is collapsed.
- The plain third column combines entity, quest, story, and mission filters
  with minimap, elevation, surface, water, point, and point-height
  controls without an inner layer container; there is no separate bottom
  filter dock. The outer panel body owns scrolling for all three columns.
- Each available raster layer occupies one row with a visibility checkbox and
  its own opacity slider. Layer opacity persists while switching maps and does
  not reset when that layer is temporarily hidden.
- Authored floor overlays are discovered by hovering their covered area and
  cycled locally by clicking; there is no global floor slider.
- Quest routes are grouped by mission and ordered by authored `questOrder`.
  Shared-file or shared-script relation webs are not rendered.
- NPC proxies with explicit `npcProxyDialogAttachments` expose their owning
  mission and quest ids as selectable phases. The selector does not derive an
  order from proxy ids, registration order, or coordinates.
- Entity size is independent from map zoom. Layer opacity and the two-thumb
  point world-Y filter change presentation only.
- Map01, Map02, and config-proven shared blackbox scenes stitch by exact
  `regionKey`. Dungeon maps with a source-art dependency remain independent.
- The bottom-centre range switch defaults Map01/Map02 to the selected zone.
  `All zones` explicitly loads and stitches every Wuling or Valley-IV member;
  switching back releases cached sibling payloads as well as removing them
  from the rendered surface.
- Minimap/model/water rectangles and markers all use X/Z with image top at +Z.
  `needInverseXZ` applies the evidenced quarter-turn consistently.
- The inspector keeps strong identity links separate from weak spatial or
  mission context and never upgrades proximity into ownership.
- Map-wide files and weak file links are debug-only unless the file has an
  exact generated Story deep link; disabling debug also closes any file viewer
  whose link is no longer visible.

Evidence boundaries:

- A registry or InitChunkData transform proves placement, not visibility,
  interactivity, prefab identity, or renderer ownership.
- Static OBJ projection requires an exact matrix and mesh relation. Material
  color requires one unambiguous Mesh → Material → base texture path plus UVs.
- HLOD exports without an exact instance matrix remain diagnostic only. Map01
- HLOD exports without an exact instance matrix remain diagnostic only. Map01
  and Map02 now join each exported cluster to its `InitChunkData` 4x4 matrix by
  exact level, HLOD level, grid i/j, and signed cluster hash; unmatched or
  non-unique rows are omitted without a name-prefix or spatial fallback.
- Seamless Map01/Map02 members vote on a shared HLOD origin, but a member uses
  that origin only when its own multi-LOD marker coverage remains within the
  accepted fit tolerance. Rejected regional origins and their bounded coverage
  are retained in the render manifest instead of silently shifting a local
  grid by one cell.
- Danger-map surfaces state their evidence grade in the task column: inferred
  source-art HLOD crop, exact streaming mesh with unverified color, or exact
  streaming mesh with partial recovered base color. `dung01_wrdg001` prefers
  its exact streaming projection; its older inferred HLOD remains diagnostic.
- e0m0 HLOD clusters use the generated assets' exact level/LOD/signed-suffix
  contract to bind each cluster to one generated material, then follow that
  material's `_BaseColorMap` PathID to the exported diffuse atlas. Missing or
  duplicate links fail closed to the elevation palette. This recovers unlit
  base color, not the game's environment lighting or post-processing.
- The same generated-material contract is applied to every published HLOD
  source and independent crop. Current indexed HLOD clusters all resolve
  uniquely; unresolved or duplicate future exports still fail closed.
- HLOD point overlays retain a deterministic sparse sample set for every
  projected pixel and elevation. The normal full-range view uses the compact
  sample sidecar; the browser groups samples into shallow height slabs and
  alpha-composites those slabs from low to high. A bounded height filter omits
  excluded slabs, so removing an upper layer reveals co-projected geometry
  below it instead of retaining the upper layer's raster coverage.
- Map01 and Map02 use exact `UILevelMapLoadConfig` world rectangles for their
  authored minimaps and exact `InitChunkData` matrices for recovered HLOD
  geometry. Surface/elevation layers retain all successfully joined triangles;
  the point layer samples those exact transformed surfaces on a deterministic
  world-space X/Z lattice. `--surface-point-density N` controls samples per
  square metre (default `0.25`, approximately 2 m spacing) without changing
  transforms or alignment. Point sampling excludes named floor, roof,
  ceiling, ground, and terrain meshes plus broad near-horizontal non-prop
  slabs from the point layer only; material and grayscale elevation layers
  retain floors and the remaining recovered environment surface while omitting
  explicitly named roof/ceiling covers.
  Levels without in-game minimaps retain an exact registry/quest
  transform point layer when an inferred HLOD surface is suppressed.
  The frontend applies no image-registration scale or translation. A level
  with no exact Mesh join remains transform points only rather than falling
  back to inferred geometry.
- Water requires both authored minimap water pixels and exact WaterData scene
  evidence. Packed flowmaps alone are not coverage.
- Explicitly named roof/ceiling instances are omitted from every recovered
  geometry layer. Broad near-horizontal structural slabs are additionally
  omitted from the point presentation only; floors remain in material and
  grayscale elevation layers.

Maintained commands:

```bat
python scripts\recover_map_streaming_instances.py --level LEVEL --jobs N
python scripts\build_map_recovery_preview.py
python scripts\build_map_recovery_preview.py --level LEVEL
python scripts\build_map_recovery_preview.py --surface-point-density 0.25
python scripts\build_map_recovery_data.py
python scripts\build_map_recovery_data.py --level LEVEL
```

Use `build_map_recovery_data.py --with-preview` to publish map data, render
previews, and attach the current render manifests without a second evidence
build. `--preview-only` reuses current map payloads. Focused `--level` runs
preserve unrelated generated maps; full runs remove stale map JSON and minimap
composites.
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

`export_assets.bat` assumes generated Story and Story evidence are current. It
rebuilds every downstream semantic view: Mission Pipeline, map recovery,
Characters, Gameplay/projectiles, Assets/audio, the curated source graph, and
debug-only combat relationships. Use `--from-game` to refresh decoded assets
and audio first only when the structured Story/Table export already matches
that installed build; asset-only extraction never advances structured-data
freshness provenance.

`--mission-pipeline-data-only` validates the current protocol registry and
rebuilds Mission Pipeline/map JSON, but deliberately skips Story gap-evidence
refresh and map preview rendering.

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
