# WebUI recovery

## Current status

The static WebUI is the project’s primary surface. Story, Characters, Gameplay,
Audio, Assets, Text, and Updates are normal pages. Mission Pipeline is
experimental and appears only with `Show debug info`; Audio and Mission
Pipeline retain visible under-construction labels.

Story, localized references, character identities, gameplay semantics, assets,
audio, and update comparisons build reproducibly from a current
`export_full/`. Optional datasets fail visibly when absent or stale.

Story recovery uses unique case-insensitive resource-name matching by default
while preserving authored spelling in evidence. The Story page may label an
authored cutscene definition as unused only after a complete, non-degraded
playback-carrier census finds no exact or uniquely folded reference. Missing,
stale, ambiguous, or failed scans remain unresolved and never auto-mark unused.

Mission Pipeline currently keeps 152 exact native-playback Story files visibly
unowned. Current reverse-PPtr, carrier, LevelData/SubGame, MissionRuntime,
IFix, and protobuf evidence closes playback context but supplies no promotable
mission/quest owner; the UI must retain that ownership gap. Each file now also
shows its active-overlay trigger confirmation: exact local volume geometry when
spatial, or the exact non-spatial event carrier, together with source/hash
evidence. These confirmations remain explicitly non-owning and non-ordering.
The spatial Story map renders decoded authored volume outlines and keeps exact
non-spatial carriers separate from the actionable no-trigger-lead queue.

Retired Progression and Combat & Projectiles pages stay retired. Their useful
progression, projectile, asset, and sound information lives in Gameplay.

## Build and serve

```bat
.\setup_first_time.bat
.\export.bat
.\export.bat --from-game --with-assets
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
.\export_assets.bat
python serve.py
python scripts\pack_webui.py
```

When Story bundles and evidence are already current, `export_assets.bat`
rebuilds all downstream semantic views, including Mission Pipeline/map,
Characters, Gameplay/projectiles, Assets/audio, the curated source graph, and
debug-only combat relationships; `--from-game` refreshes decoded assets first
without changing the structured Story/Table freshness fingerprint. The
Mission Pipeline data-only scope reuses current evidence and previews rather
than refreshing either one.

Before a builder reads an existing extraction, verify freshness with
`python scripts\verify_export_freshness.py`. Reuse an existing server at
`http://127.0.0.1:8765/` instead of starting another default instance.

## Stable data contracts

Primary generated data:

```text
webui/data/manifest.json
webui/data/lang/<LANG>/{index.json,conv/,mission/,reference/}
webui/data/lang/<LANG>/characters/index.json
webui/data/lang/<LANG>/gameplay/**
webui/data/lang/<LANG>/audio/{index,events,media}.json
webui/data/mission_pipeline/{index.json,missions/}
webui/data/assets/{index,gameplay_refs,story_media,videos}.json
webui/data/updates/latest.json
```

User-managed inputs:

- `webui/overrides/story_order.json`: active Story order; never regenerated.
- `webui/overrides/options.json`: manual option positions and responses.
- `webui/overrides/narrative_videos.json`: narrative-video attachment policy.
- Character merge/name overrides: live inputs written through `serve.py`.

Schema changes must update the builder and consumer together. Optional sidecars
must produce an explicit unavailable or degraded state instead of silent empty
data.

## Stable frontend behavior

- Disabling debug mode while Mission Pipeline is active returns to a normal
  page and normalizes the URL.
- Story issue and recovery-method filters remain visible; raw source blocks,
  Timeline evidence, cutscene diagnostics, and order tools remain debug-only.
- Manual option coverage adds its own filterable Story tag while preserving
  generated option-evidence classifications and counts, including
  unregistered table-only placement.
- Mission Pipeline CallServer rows retain exact preceding-Story path context
  and rejection diagnostics. Only a unique linear Story -> CallServer ->
  callback -> Story closure may enter the source-order graph; the current
  corpus has no such two-ended closure.
- Mission Pipeline source-order evidence uses the active LevelScript overlay;
  changed Persistent files replace shadowed StreamingAssets actions rather
  than merging both versions. Rejected stale edges remain diagnostic instead
  of being relabeled as active evidence.
- Story reset restores Story sort and default filters while preserving expanded
  mission groups.
- `sns_emoji_*` stays inline without hover/modal preview. Other SNS media keeps
  natural proportions with bounded previews.
- Characters keeps identity provenance and live override behavior.
- Gameplay owns progression, projectile, asset, and sound presentation. Exact
  and inferred ownership are labeled separately.
- Enemy level controls show only authored points; variants resolve their exact
  attribute template before displaying stats.
- Active-skill level panes show positive authored cooldowns. Enemy born-Buff
  cards show exact decoded lifecycle/stacking/trigger fields, keyed numeric
  candidates, exact attribute modifiers and raw applied tag ids. The current
  GameplayTagPredefineTable plus the serialized GameplayTagConfig object-index
  paths provide exact names for covered IDs (2,584 current merged IDs). Missing
  immunity paths are named only when an exact `tagName2Immune` status context
  independently proves the `Immune/<suffix>` CRC32; those rows are visibly
  context-derived. Other IDs stay unresolved. Unresolved tag chips retain the raw ID and
  expose the structured “not in current serialized GameplayTagConfig” reason
  on hover, plus fully
  validated runtime GameplayTag captures may be passed explicitly to the base
  builder to add exact runtime name/id pairs; the UI keeps those rows visibly
  runtime-sourced rather than treating them as serialized config evidence.
  consumed non-empty action chains. The visible action vocabulary now includes
  cooldown operations, Buff-id/stack/HP/poise/damage/tag/distance conditions,
  timed markers, resource and blackboard operations, skill casts, effects,
  created/finished Buff ids, bounded damage actions, and selectors. If/Else
  branches are traversed for display instead of hiding their nested exact
  actions. Common TargetSettings envelopes now show their exact target/group,
  context, owner, source, and selector fields even when the enclosing action
  remains partial. Current native enums label events and recovered modes;
  ModifyDynamicBlackboard now labels the native HpRatio calculation type and
  all seven current operations (including Floor, Ceil, and RoundToInt);
  ConvertToTargetContext rows also label the current target-conversion and
  translation-rotation enum values;
  CompareFloat actions expose their exact Beyond.CompareType and are visible
  as blackboard comparisons;
  SimpleCalcBBAction uses its decoded Add/Multiply/etc. operation instead of a
  fixed division glyph;
  SpellInfliction rows label the current Fire/Pulse/Cryst/Natural elemental
  infliction enum when present;
  complex entity spawn, projectile, heal, DamageUnit/EffectActionCfg, unknown
  selector subtypes, and unmapped tag names keep a visible unresolved
  boundary.
- Enemy modifier chips use current gated native enum meanings with authored
  values, while final runtime values remain intentionally uncomputed across
  other buffs and IFix.

## Audio evidence boundary

The Audio detail pane supports searchable per-record manual notes persisted in
`webui/overrides/audio_notes.json`; the list shows each note's first line beside
the filename. Its playable-media section is the first section of a selected
record panel, before the Details heading, manual notes, and evidence facts, so
the player is available at the start of the detail pane. These annotations are
user research state and do not upgrade or modify generated evidence.

Audio separates Event/media identity, Wwise graph relation, authored consumer,
and observed runtime execution. A stronger layer never appears unless its typed
evidence exists.
The semantic publisher can consume a verified offline audio-trace bundle. It
then marks the exact captured managed request on Event details and propagates
only the matching Event relation to media details. Unverified, mismatched, or
language-incompatible bundles remain degraded and do not create bindings;
observed requests still do not prove branch selection or audibility.

The current pipeline can join raw HIRC Events, decoded media, AudioDialog and
responsive-voice tables, Timeline audio, Lua consumers, selected serialized
components, gameplay actions, and fingerprint-locked native callsites. Direct
and conditional native consumers retain their method, callsite, target, and
branch evidence. Selector and dictionary paths stay distinct from direct
literal playback.

Ordinary Audio details show authored AudioCue behavior Event requests and
string-literal/variable-name controls as typed evidence. Scene-emitter detail
data keeps prefab source and source-status separate from scene ownership. Event
and Media search/detail evidence now visibly shows `sceneContainmentStatus`,
the exact prefab `sourceAssetPath`, and its container type, while explicitly
labeling runtime scene instantiation as unobserved. A source prefab row must
not be presented as a recovered level instance. The complete validated AudioCue
tree, raw scalar fields, source coordinates, node classes, native-name gate
status, and bounded diagnostics are
lazy detail data shown only in the debug surface; compact rows retain bounded
summary fields. Non-empty behavior `exprType=3` leaves show authored Event
requests, non-empty `exprType=8` leaves show `runtimeCueVariable`, and
`childrenLimit` prevents descendant projection. Exact native enum/operator
names appear only under the validated selected-input gate; missing or
mismatched inputs leave them absent. Selected condition truth,
handler/indirect dispatch, runtime variable values, cue execution, Wwise branch
selection, and audibility remain runtime-blocked and are not presented as
observed facts.

Scene-emitter cards and details now show compact containment/prefab-identity
status sets. The current offline result is visibly a prefab-local static
emitter with scene unresolved and prefab identity unavailable, never an exact
scene tag. The recovery queue remains blocked on a future exact
SceneAsset/Level containment or prefab Source+PathID-to-level relation; names,
candidate paths, positions, and sidecar level IDs remain non-evidence.

Scene-global Event summaries and cards expose all exact authored scene IDs and
original semantic-role names only when every direct context passes the merged
scene-catalog gate. Search and context filters use that same exact status;
malformed, partial, non-direct, truncated, and out-of-catalog contexts remain
unavailable diagnostics and do not imply runtime activation, branch choice,
playback, or audibility.

Normal Audio records also include a collapsed LevelScript audio lifecycle
section for authored producer/consumer links, serialized action ordinals, and
validated static topology. Raw serialized output paths, record offsets, and
local IDs stay debug-only. Runtime handle values/state, action execution,
branch selection, and audibility remain blocked, so the section is not a live
playback trace.
RemoteCommon `startAudioEvent`/`endAudioEvent` fields are displayed as
separate authored lifecycle contexts after the exact Persistent-over-Streaming
row overlay. The current CN page data has four such rows, all found in Wwise
music Events and none with a playable media leaf; runtime execution remains
unobserved.

Serialized `monoBehaviourAudioIdField` context chips expose the narrow authored
field role, `componentLayout`, component type, and raw serialized path. Search
also covers the raw field/path evidence and generic serialized-field rows
(including an audio-key hint);
details show GameObject, hierarchy, and world position only when the existing
placement fields are exact. These labels describe authored serialized fields,
not callback execution or Event posting, and generated coverage counts remain
in Audio data rather than this memory topic.
Exact AudioMapData trigger/lifecycle/room-tone fields use the same visible
context surface only after their complete serialized schema validates; numeric
matches from incomplete lookalike components remain absent.

Streaming-instance sidecars retain exact entity/name/transform and bounded raw
ECS evidence, but the currently validated InitChunkData columns expose no known
prefab Source+PathID/hash field in the observed schema. The Audio page accepts
a level-instance relation only from an explicit numeric identity, optionally
resolved to one unique full AssetMap container path or explicit component
identity; names, basenames, positions, Meshes, and similarity remain
non-evidence. A separately proven StreamingChunkData record-to-entity relation
is still a recovery gap. If explicit component identity and exact prefab-path
identity routes disagree, the visible join remains unavailable with
`conflictingPrefabInstanceIdentityJoins`. Current CN data therefore exposes
zero exact scene-emitter Events and 43 prefab-local Events; the next recovery
step is exact prefab identity from exporter/sidecar output, not filename/path
inference.

Missing or mismatched installed native inputs never erase authored Audio rows.
They suppress only build-locked callsites/mappings and expose a bounded
unavailable diagnostic, so the page cannot silently present stale native
addresses as current evidence.

ModelView normal Event contexts show the authored controller/model/layer/state
chain and `behaviorTime` with explicit labels: `Authored`, `static route`,
`runtime unobserved`, and `branch unresolved`. The static route is shown only
for the fingerprint-locked `AudioBehavior.Execute` → `AudioManager.PostEvent`
contract; execution, branch choice, and audibility are not inferred. The
runtime overview publishes no `nativePairing` unless a complete
hash-verified closed capture session exists; partial key/path/handle/decoder
overlaps remain unobserved.

Positioned ModelView audio is shown with three authored branches. A direct
position Event with a nonzero `normalAudioId` exposes independently audited
`PlaySoundAtPosition` endpoints and an `m_audioHandle` store; these are separate
static facts, not a recovered chain. Custom and entity forms are control-only;
`_SwitchState` has no recovered playback sink, and neither form promotes an
Event, media leaf, or owner. The managed `PostAndForget` →
`AudioAdapter._PostEvent` route is statically verified through the managed
internal playing id, Adapter guards, and the `LoadBank`/`PrepareEvent`
boundary. The runtime completion delegate, final
`AkSoundEngine.PostEvent`/native playing-id handoff, Wwise selection,
execution, and audibility remain unresolved.

Responsive voice contexts also expose exact matching `AIBark` request rows and
the fingerprint-locked native dispatch chain. The UI must keep the live
AIBarkType-to-bark-id dictionary choice, probability/cooldown selection, and
actual response branch unresolved; similarly named enemy voice definitions are
not AIBark evidence unless their trigger key occurs in the authored table. The
audio trigger catalog reports story-bound responses as resolved terminal,
direct/Wwise-only responses separately, and missing configured response ids as
non-playable authored gaps.

The runtime overview also exposes the unnamed current-build string+callback
helper shared by Timeline and voice callers. It is shown as an alternate entry
into the hash/`_PostEvent` chain, with no fabricated method index or managed
owner; execution, callback flags, selected branch, and audibility remain
unobserved. The external-source chain likewise shows the voice preparation and
external-source-key/path resolution helper as alternate entries; the page
keeps their callback mask and resolver role static-only.

Responsive rows whose trigger key is one of the five exact
`EnemyTriggerVoiceAction` dictionary values now retain its numeric voice type
and native mapping callsite. Separate fixed native response callers cover
low-HP/stun, enemy battle-entry yell, patrol running, reach-core, and
leave-battle flee. Two `common_attack` rows are already resolved by exact
ResponsiveDialog membership; the other 34 `common_attack`/`common_escape` rows
remain definition-only highest-priority unknown-purpose rows because neither
exact native path names them.

Exact Wwise graph traversal proves possible media leaves, not the live
switch/random branch or audibility. String literals, definitions, lookup keys,
and same-name assets remain identity-only until they reach a typed playback
consumer. Shared media and language voice remain separate, and duplicate media
IDs retain physical package provenance.

Event evidence also exposes exact direct NodeBase processing: ordered effect
slots, resolved built-in plug-in names, parameter fingerprints, and explicit
output-bus routes. Gain, Delay, Compressor, Expander, three-band Parametric EQ,
Meter, Matrix Reverb, Pitch Shifter, Harmonizer, and Stereo Delay rows show
exact authored base settings decoded from fingerprinted shipped
`SetParamsBlock` layouts. RoomVerb rows show all public authoring controls and
the exact embedded ER pattern name, but keep private SetParam IDs 100..110
visibly meaning-unresolved. Their debug payload now retains native use roles:
five tap-pattern inputs with seeded variation and ER-grid normalization, one
six-channel coefficient input, two seeded secondary reflection-pattern inputs,
and three IDs with no direct read in the audited update helpers. Guitar
Distortion definitions expose all six
pre/post EQ bands and their Type/Drive/Tone/Rectification/Output/Mix controls.
Convolution Reverb rows expose 13 public runtime controls. The two private rows
now retain native forwarding evidence: SetParam 34 is copied through native
+0x3c/wrapper +0x4c and forwarded on both convolution processing paths, while
the final serialized byte is copied through native +0x40/wrapper +0x50 into
runtime state (+0x8c). The current CPU consumer does not expose a read of the forwarded
scalar, so neither private row receives an invented public name or DSP claim.
The overview lists exact impulse-response plug-in media dependencies separately
from playable WEM leaves. Overview and
event summaries distinguish exact, partial, and opaque parameter semantics.
Mastering Suite rows expose the four public output-device modules, including
six EQ bands, four multiband-compressor bands, master/channel gains, and limiter
settings. The two private codes show exact native storage offsets (+0x18/+0x88)
but no direct runtime read in the audited region, so the UI marks them
storage-only; channel-speaker names also remain explicitly unresolved. All 732
current CN effect definitions are now decoded (698 exact,
34 partial, zero opaque). Physical PCK path remains part of effect-definition
identity so Audit and Hotfix rows with reused numeric IDs do not collapse. The
Event cards now decode v150 FX-slot bit vectors as authored bypass, ShareSet,
and rendered flags: 12/279/890 direct-slot occurrences respectively, plus
8 bypass and 89 ShareSet bits on resolved Audio/Aux Bus slots. Unknown bits are
reported separately; rendered does not claim runtime DSP execution or
audibility, and all slot flags stay separate from node-level bypassAll and
dynamic BypassFX. The
UI now resolves each explicit output bus through the complete 279-definition
Audio/Aux Bus parent hierarchy and shows the recovered DSP at each stage. The
current corpus has 276 exact non-root parent edges, three roots, and 151 buses
with 247 cross-correlated non-empty effect slots; all 247 expose decoded authored
settings. Exact sibling-payload prefix/suffix correlation additionally proves
typed v150 `CAkBus` parsing now proves the serialized InitialFX count on all 279
buses: 128 explicit empty lists and 151 non-empty lists with 247 decoded slots.
The same Bus rows expose authored properties, duck records, recovery/max-duck
values, and exact InitialFX offsets. Bus details now also expose the exact v150
InitialRTPC-before-StateChunk suffix:
all 279 Bus definitions parse, covering 92 curves/265 points, 15 State groups,
32 States, and 34 authored State values. Standard control labels are shown.
The out-of-range `0x1802`/`0x1804` IDs are surfaced as custom/internal
parameters: the current index counts 90 node curves for each, six Bus State
properties for `0x1802`, two for `0x1804`, and one Bus InitialRTPC curve for
`0x1804`; no DSP-property name is inferred and runtime selection is not
inferred.
The same index now publishes a hash-pinned IL2CPP metadata cross-match for six
game-side GameParameter symbols: `AU_RTPC_CINE_CTRL_VOL_AMB` (`0x6b7dc358`,
3 node/4 Bus curves), `...VOL_MU` (`0x590f4cd1`, 2 Bus curves), `...VOL_SFX`
(`0x52aabb05`, 11 Bus curves), `...IS_MUTE_BY_SDK_WEBVIEW` (`0xba4a40b7`,
1 Bus curve), `...IS_SURROUND_CHANNELS` (`0x7ec2f9aa`, 2 Bus curves), and
`...GLOBAL_VOL_MASTER_IOS_WORKAROUND` (`0x3794392f`, 1 Bus curve). This is
symbol-to-ID evidence only; it intentionally leaves `0x1802`/`0x1804` as
custom/internal Wwise property IDs and does not claim live updates.
Event/media RTPC and Bus-control detail rows reuse this catalog; unmatched
controls stay numeric/custom rather than receiving inferred names.
The semantic Event projection also recovers 25 unique `AU_*` IL2CPP field
symbols whose exact AudioHashGenerator hashes match current Wwise Event
objects. Their declaring type, field token, and symbol evidence are shown in
Event details and reused for conservative name-prefix categories (including
conveyor/laser/NPC SFX, UI scan, Qinshi/mastering controls). This proves static
symbol-to-ID identity only; the field does not prove a runtime setter, caller,
trigger, selected branch, execution, or audibility.
Eighteen Event rows additionally carry exact current-build native custom-state
callsite evidence from `InteractiveLogicBase.SwitchAudioCustomState`, covering
rotate-platform, crane, electric-fence, ForgeIron, LifterButton, and
MovingPlatform state machines. The trigger catalog retains method/callsite VAs
and metadata usage words only after joining authored `InteractiveData` custom
states. `RotateNormalStart` and `RotateOverStart` remain separate
branch-specific states at one callsite; branch execution, object ownership,
and audible output remain unobserved. The same fingerprint-locked catalog
places the pause/resume control Events `au_gameplay_pause_spidle` and
`au_gameplay_resume_spidle` at exact `SnapshotSystem` `PostEvent` callsites;
action-entity ownership and runtime execution remain unobserved.
The former last CN `purposeKnowledgeStatus=unknownUse` row,
`au_voice_c35m3_3_001` (`v1d4/Narrating/HS_Part04/c35m3/...wem`), now has the
exact coarse ownership `missionNarrationVoice` and status
`coarseOwnershipKnown`. There is still no AudioDialog, Story-line, or
trigger-context edge, so `playbackLocationStatus` remains unknown. Audio media rows
separately expose searchable coarse ownership for exact scene, animation,
component, interaction, UI, voice, and mission-narration evidence. This avoids
treating an unknown SFX/music category as wholly unknown use while preserving
the runtime selection and audibility boundary.
The Audio page also exposes exact same-name AnimationClip action matches. The
current closed set contains five callback-backed Event identities and eight
possible media leaves; details retain the clip, actor, and evidence fields.
These rows are action SFX, but Animator execution, Wwise branch selection, and
audibility remain unobserved.
Audio Event and media details now also expose CharacterTable-backed ownership
for authored `chr_*`/`au_chr_*` namespaces. Search covers the character id and
token, and shared Wwise media lists every named character owner. A unique
numeric-prefix recovery is labeled separately from a full-key match; generic
templates and action/playback claims remain unresolved without their own
evidence.
The same visible ownership now covers uniquely owned `au_actor_<token>_*`
Events and Event-leading character tokens such as `lastrite_*`, `lizhiyan_*`,
and `pograni_*`. Supported
AnimationClip audio callbacks are projected independently of same-name action
matching, so normal Event/media details retain their exact clips, callback
owner/function, reachability, and AnimatorController names without claiming
runtime execution or forcing an unknown category to SFX.
Gameplay character cards reuse the exact CharacterTable namespace evidence as
a separate collapsed authored-namespace audio group with playable media. Those
rows are not mixed into skill or animation-triggered SFX and visibly retain the
unresolved action, Event-post, Wwise-selection, and playback boundary.
Enemy cards now have the same separate surface for recovered `au_` names with
an exact full EnemyTable-id prefix. Because these names are grammar/hash
recovery rather than consumer evidence, the UI retains the identity-only label
and does not promote them to enemy skill or animation playback.
Audio detail keeps each callback Clip's resolved entity IDs separate from its
candidate entity IDs. Exact Character/Enemy/EnemyTemplate overlay matches are
resolved; unique-token or multi-match identities remain candidate/ambiguous,
and callbacks shared by multiple authored owners retain a shared label.
Missing or malformed overlay data and unsupported Clip tokens stay unresolved
and fail closed. The visible callback relation is authored static evidence;
Animator execution, callback timing, Wwise branch/media selection, playback,
and audibility remain runtime-unobserved.
When the two NPC tables provide one exact agreeing row, the Audio page also
shows `ownerKind=npc`, NPC id, template, and actor token for the callback Clip
only when the same token has one exact `AudioDialogChannel` key. Duplicate or
generic tokens, missing channel identity, overlay conflicts, malformed rows,
and template mismatches stay unresolved. Mixed Events keep the NPC identity on the
occurrence/Clip evidence instead of promoting the whole Event to one owner.
Event rows
now distinguish serialized User-Defined Aux
slots from Game-Defined send enablement: the current unique-node corpus has
7,492 populated User slots to 25 Aux Buses and 30,162 Game-Defined Use bits.
User targets show their exact bus/DSP chain. Game-Defined targets, listeners,
and levels stay visibly runtime-assigned instead of being invented; current
Early Reflections Bus references are zero. Effective inheritance and live
bypass/RTPC/State values are not presented as observed runtime state. Event
possible-media rows now carry a compact projection of their exact serialized
Event output-bus paths, effect-bus IDs, and unresolved bus-processing IDs, so a
decoded audio file can be inspected against its post-processing route without
duplicating the full HIRC catalog. This remains a possible authored route when
the Event has random/switch/sequence branches; runtime selection, effective
inheritance, and audibility are not claimed. Media rows also carry a bounded
exact `trigger_contexts.json` `mediaRefs` summary of semantic kinds, roles,
owner/situation values, and selection/activation statuses; this is still an
authored request/placement join, not observed execution. Wwise media leaves
also carry exact serialized edge types and selection paths (`directSound`,
`layerChild`, `randomAlternative`, `switchCandidate`, sequence/music edges)
plus root Action IDs: 59,109 CN media rows have graph evidence and 39,619 path
summaries. This identifies how a leaf becomes an authored Event candidate
without claiming runtime branch choice, caller identity, or audibility. Media
rows whose typed
Event-level authored context is now also projected onto the possible media set:
44,442 CN media rows carry 367,317 context occurrences with compact kinds,
roles, owner values, and situation values. This is intentionally broader than
exact `mediaRefs`; it explains Event consumers without claiming that each
listed context selected the individual leaf.
Complete final-media leaf-set equivalence additionally recovers a uniform broad
category for 85 hash-only Events (56 SFX, 21 UI, 6 voice, 2 control), while
leaving their caller, trigger, branch, and runtime purpose unknown.
The projection also retains weak category-name evidence on 954 named Events
from enemy, actor/UI, LevelSequence, and Gameplay-SFX families; exact voice
contexts take precedence on 602 enemy-named rows without discarding the name
evidence.
Unknown physical media paths now receive a separate evidence-backed semantic
category: 40,421 rows (34,458 SFX, 5,645 voice, 188 UI, 66 ambience, 48 control,
13 music, 3 cue). This is 40,217 uniform related-Event joins, four exact
trigger-context Event categories, and 200 exact MonoBehaviour audio-field
roles. The raw path category stays unchanged; 276 mixed known-category rows
remain unresolved.
NodeBase evidence has zero serialized output-bus nodes now retain an explicit
`noExplicitOutputBusSerialized` status; default/parent routing, silence, and
effect-free behavior remain unresolved. Event details also render exact
Media details now separately render bounded direct NodeBase effect slots from
Event `postProcessSummary.effectNodes`, preserving effect/plugin, node/slot,
authored parameter summaries, and slot flags. This is an exact serialized
effect join, distinct from output-Bus effects, and does not prove live DSP
execution or audibility. Event details also render exact authored base
AkPropID values and min/max ranges with raw U32 plus finite-float
interpretations (typed ID/integer unions remain integer-labelled). The current
CN build exposes direct effects on 1,879 media rows with 471,281 slot
occurrences; each row keeps at most 32 distinct summaries and marks truncation
explicitly. A compact serialized effect-chain view now combines those direct
slots with each media leaf-to-root Bus path: 32,044 CN media rows expose
573,360 authored chain stages, capped at 64 per row with explicit truncation.
Direct-node slots precede Bus slots in this display, while Bus slots retain
serialized path/slot order; it is not observed runtime DSP order or audibility.
The same rows carry compact Bus-control references: 31,523 CN media rows expose
135,375 controlled-Bus occurrences, 332,954 RTPC curve occurrences, and 5,616
State values. Full curve points and plug-in parameters stay in the unique Bus
catalog and are resolved by ID rather than duplicated in every media row.
Media details also carry exact serialized Bus ducking references: 1,909 CN
media rows reach 2,249 ducking Bus definitions with 4,453 authored duck slots,
including target Bus, attenuation, fade, and target-property fields. The
projection remains a possible route; runtime duck activation and audibility
are not observed.
Exact User-Defined Aux slots are now projected too: 20,588 CN media rows carry
27,592 unique Aux Bus/slot targets representing 698,886 underlying send
occurrences. The compact rows retain source-node types, flags, root Actions,
and target Bus IDs; Game-Defined IDs and live send levels remain runtime-only.
Every target also carries its exact serialized Aux Bus parent path and
effect-Bus IDs, linking the possible send route into the typed Bus/DSP catalog.
Media rows now also summarize authored NodeBase properties and ranges: 53,882
CN rows expose 715,175 distinct property signatures across 18,436,139
occurrences, and 21,526 rows expose 48,721 range signatures across 113,639
occurrences. Raw U32 forms and complete node provenance remain in Event detail.
The same media projection now publishes bounded exact StateChunk override rows
and InitialRTPC response curves from the possible Event path: 4,300 media rows
carry 20,254 distinct RTPC control summaries and 1,292 carry 2,339 State-value
overrides. Curve points are capped per row with explicit truncation; the join
proves authored serialized controls only, not live setters, selected branches,
inherited values, platform DSP, or audibility. The current traversed view contains
90,639 property-bearing nodes, 165,161 values, and 1,650 ranges. Initial
BypassFX/BypassAllFX property IDs are absent in this corpus, so the UI keeps
direct bypass flags separate from unresolved dynamic bypass. Event details
now also render exact StateChunk overrides and InitialRTPC response
curves. The overview reports 236,650/236,650 parsed node occurrences, 1,784
State Group references with 1,640 property values, and 19,001 RTPC curves with
67,327 points. Known hashes receive names only through existing exact evidence:
the gamepad backend group labels XInput/ScePad states, and known `au_rtpc_*`
parameters label their matching curves. Every row retains the boundary that
live State/RTPC/modulator values, inherited effective properties, bypass, and
audibility were not observed.

Event cards now also render exact v150 non-playback Action tails from the
original bank bytes. Playback and control rows include the typed serialized
Event→Action path and target object type, so the trigger edge is visible without
claiming runtime execution. The current named-event output contains 6,735 typed
control actions, including SetState/SetSwitch IDs, GameParameter ranges and
fade policy, Stop/Pause/Resume flags, Seek, authored value/filter controls,
exception buses, and FX slot bypass/indices. These rows explain serialized
dispatch intent only; runtime state, selector choice, effective inheritance,
DSP execution, and audibility remain explicitly unresolved. Malformed or
unsupported tails stay fail-closed with their parser offset and reason.
The projection joins 1,601 Action group references and 1,042 exact value
references in the current CN output. It labels the three native-backed
selector roles plus the ten current-metadata music State groups; the same
15-row catalog labels typed type-6 package branches (including XInput/ScePad
and music enum members) when an exact value is available. Unmatched IDs remain
visibly numeric.
Ordinary Audio Event details show authored Type-6 candidates in a collapsed
`Possible State/Switch branches` section. Raw object/group/value IDs and
ownership/parser evidence stay debug-only; inferred catalog labels remain
possible rather than exact. The selected runtime branch and audibility are
runtime-blocked and are not presented as observed facts.
The current CN projection also marks 12 same-event Set/ResetGameParameter →
InitialRTPC exact-ID joins (2 unique IDs) as authored curve targets. It does
not invent a parameter name or claim a live value/effective DSP response.
The control catalog additionally publishes five exact metadata-named
InitialRTPC parameters (14 curve occurrences across six Event occurrences),
with their trigger contexts, controlled properties, response-point totals, and
interpolation labels.

The Audio view now uses purpose-priority ordering and explicit unknown,
partial, known, and Story-line-terminal filters. Story-line binding ends
purpose investigation for that media. Playback groups with at most 20
candidates remain expanded and materialized; only groups above that threshold
start collapsed. The runtime overview and responsive context rows expose the
exact five-entry `EnemyTriggerVoiceAction` mapping without upgrading it to a
live branch observation. In a selected Audio record, the playable-media
section is rendered before the Details heading and the longer facts/evidence
list.

## Story and Mission Pipeline boundary

Story combines authored dialog structures, Timeline placement, mission/runtime
links, localized references, and manual order without flattening their evidence
types. Cutscene shapes, subtitle evidence, definition-only media, authored
placement, and runtime activation remain distinct.

Mission Pipeline shows typed trigger chains and their ownership/activation
gaps. Native registration, source order, code address, proximity, OCR, and
manual order never become mission chronology by themselves. Weak placement is
visually separate and cannot override exact placement.

## Map

Map is a normal page after Story. It uses one generated contract for all levels:
registry, quest, mission, minimap, HLOD, and streaming-instance evidence remain
typed instead of being flattened into a generic location claim.

Current state:

- Level ownership comes from `LevelBasicInfoTable.idNum` and registry ids;
  shared scene ownership comes only from the current compact LevelConfig path.
- Map01, Map02, and config-proven blackbox scenes stitch by published
  `regionKey`. Non-seamless dungeon and danger maps remain independent even
  when they reuse source art.
- The browser derives the active world rectangle from loaded backgrounds and
  projects backgrounds, markers, labels, routes, floors, and model layers with
  the same X/Z transform.
- Minimap, grayscale elevation, material/surface, water, and point layers stay
  independent. Each available layer has one row with a visibility checkbox and
  persistent opacity slider. Point layers additionally own exact world-Y
  samples so filtering an upper band can reveal lower co-projected geometry.
- Current streaming sidecars are schema 2. Entity bases expose one `meshes`
  array; exact instances feed static render layers rather than duplicate UI
  nodes.
- Authored floor images are selected by spatial hover/click, not a global
  slider. Mission routes use authored quest order; co-occurrence relation webs
  stay absent.
- Mission-selected NPC proxies can be filtered by their exact attachment
  quest id. Phase rows are published only from `npcProxyDialogAttachments`;
  lexical presentation is not treated as mission chronology.
- e0m0 on `indie_dg002` now publishes the current-build validated local
  `8700010001#80002` Story trigger as its authored rotated Box footprint and
  links it to `radio_e0m0_9`. Nominal e0m0 context keeps it visible with the
  selected route while remaining explicitly separate from mission ownership,
  event firing, and observed playback.
- Exact Story-to-map publication also recognizes build-locked
  `Play3DRadio`/`Play3DRadioAndWait` records when the same complete serialized
  record contains both the `radio_*` id and an exact spatial EntityPtr. The
  current corpus publishes 105 such action links across 69 map points and 102
  Story files; one otherwise complete radio record remains unplaced because
  its world identity has no authored registry or NPC-proxy transform. Shared
  local trigger geometry is drawn once while retaining every exact Story key.
  Full active-playback enumeration now publishes 2,148 trigger markers carrying
  2,771 Story links and 2,324 unique Story keys. Six dungeon sub-levels that
  own exact trigger geometry but no `LevelBasicInfo` row are retained as
  trigger-only maps with an explicitly absent `idNum`, rather than silently
  dropping their exact Story links or inventing a level declaration. This
  includes one native-
  validated PolyLine trigger whose authored Vector2 points are world X/Z and
  are rendered directly without center translation or yaw rotation. Neither
  path inherits sibling actions, same-script files, mission context, or spatial
  proximity.
  Direct playback topology is independently checked at the action node: the
  current receiver frontier records 3,716 exact typed header-to-playback
  observations, 16 ambiguous, and 22 unresolved. `PlayRadio`, `StartDialog`,
  `PlayCutscene`, and validated direct sequence playback are eligible;
  preload, load, stop, and sibling-branch actions are inventory/context only.
- The e0m0 map audit currently covers 49 nominal CN files: 19 are placed on
  `indie_dg002`, three belong to the later `indie_dg004` context, and 27 have
  no map position. Of the unplaced set, 17 have an exact playback path from a
  non-spatial BattleSignal, GuideGroupComplete, or CustomEvent; nine Story
  files have no active serialized playback carrier; and the standalone
  `video_cs_video_e0m0_3` wrapper is already embedded under the placed
  `cutscene_e0m0_3` rather than representing a second location. There is no
  omitted exact trigger shape in this set. The highest-value recovery queue is
  the upstream producer chain for BattleSignal, custom hashes `#bb775d95` and
  `#f5c434f1`, and `TLCall_Summon_Cannon_1_Step_01`. Listener scripts, sibling
  entity actions, Story order, and proximity must not supply their position.
  Full LevelScript-corpus recovery finds `#bb775d95` and `#f5c434f1` only in
  their exact listener headers, with no serialized producer or spatial/entity
  selector. The Timeline producer after `#f5c434f1` is exact: at 7.75 seconds
  `cutscene_e0m0_13` raises `TLCall_Summon_Cannon_1_Step_01`, whose listener
  stops the sequence and plays `radio_e0m0_8d4`. This proves their relative
  chain but still cannot place either file until the external/runtime producer
  of the initial custom hash is recovered.
  The three GuideGroupComplete radios also have unique matching
  `ManuallyStartGuideGroup` producers, and the ten BattleSignal Story files
  have exact signal literals joined to the ability/buff
  `SendBattleSignalToLevel` producer family. Both are runtime-causality links,
  not spatial links: neither producer payload closes to one decoded trigger
  slot or registry-backed EntityPtr, so the safe map gain remains zero.
- Native consumer recovery confirms that `CheckIsInTriggerVolume` resolves a
  LevelScript-local trigger slot through the runtime registered-trigger id and
  TriggerVolumeManager overlap test. WorldEntityRegistry script slots are a
  separate identity domain and cannot define or upgrade trigger geometry.
- MissionArea/PosTracking schemas contain no authored script-slot identity.
  MissionArea points therefore draw only their exact MissionAreaTable shape and
  keep Story binding unresolved. Proximity rows remain debug diagnostics and
  cannot attach Story/files to a map point or produce source-backed Story order.
- `8700010002:40003` is no longer understood as a possible cutscene trigger.
  Binary evidence finds strict constant `Param<EntityPtr>` values inside
  the validated `LevelCameraLookAt` and `EntityMoveToWithDuration` action
  records, both on exact control paths from local trigger slot `80002`. The
  `0x04/0x03` are the outer `Param` and nested `EntityPtr` member counts, not
  a `ScriptEntityPtr` discriminator. The current-build native formatter bodies
  resolve those members precisely as
  `LevelCameraLookAt.lookAt1` and `EntityMoveToWithDuration._entity`; the map
  publishes the registered shell as an exact script action target. The contract
  fails closed on installed hashes and bounded formatter/setter body hashes;
  an unvalidated build falls back to the default-hidden candidate boundary.
  This proves a script action target, not player interaction. The same event
  root separately plays
  `levelseq_e0m0_watchtowerhitandfall`; that sibling sequence is not inherited
  by the point, and no `cutscene_e0m0_1`/`cutscene_e0m0_2` consumer is present.
- Action target recovery now keeps the two authored `EntityPtr` identity domains
  separate. `logicId=0/useSlotId=true` resolves only through the current
  script's registered slot; `logicId>0/useSlotId=false/slotId=0` resolves only
  through the exact global WorldEntityRegistry key. Build-locked formatter
  contracts currently add exact visibility, enable, look-at, and cast actions
  to all five e0m0 grenade towers, plus pause/AI-mode actions to enemy
  `8700050000`; the latter is also the exact target of `WaitForEntityStart`.
  The maintained contract now covers all 78 observed real action shapes,
  including entity
  show/hide, position/rotation, enemy/NPC patrol, wait, and animator actions.
  Movement/rotation, force-target, buff, positional audio, and entity tracking
  actions are also covered. Constant global targets without a registry
  transform remain explicit debug-only unplaced action rows; e0m0 currently
  includes three `EntityCastSkill._targetEntity` references to `8700040047`
  plus seven camera targets, without manufacturing coordinates for them.
  The map's technical-evidence panel is controlled by the global debug switch
  rather than a permanent HTML `hidden` attribute, so these unplaced action
  rows and their exact source-script links are visible only in debug mode.
  Exact action source LevelScripts are strong related-file pins, while
  unresolved formatter candidates remain weak. These annotations preserve the
  entity's device/enemy kind and localized label and do not add Story or
  mission ownership.
  A registry `int_empty` row with an exact action consumer is promoted to the
  visible script-target layer; only shells without an exact consumer remain in
  the default-hidden empty-slot layer.
  Camera follow/look-at, bamboo movement, entity attachment, effect attachment,
  rune-anchor source/target, Buff completion, NavMesh area, and voice target
  fields all use pinned formatter contracts. Nullable multi-entity actions are
  promoted only through a source-hashed serialized record layout that proves
  each null/constant field state; `EnterDollyTrackCamera` therefore maps its
  authored slot to `_lookAt`, while `_follow` remains explicitly null.
  The current authored spatial inventory contains 23,213 world/script/NPC-proxy
  identities. A complete corpus audit finds 1,346 with exact authored spatial
  bindings, 21,867 with no
  observed constant action reference. The last group is not claimed to be
  actionless because dynamic and opaque runtime values remain non-spatial.
  All 81 observed real EntityPtr action shapes now have native formatter
  contracts; two additional naked-byte shapes are pinned negative contracts,
  and complex nullable/multi-field records have explicit typed or source-hashed
  member layouts. Every map slot carries this observational binding status plus
  separate exact and unresolved arrays.
  The exhaustive report also retains 3,157 constant, 2,406 dynamic, 38 null,
  and 27 opaque contracted field states. Dynamic `idRef`, local-output, named
  argument, and script-variable evidence remains unplaced unless a pinned
  producer contract proves a same-header constant alias. Current contracts
  safely recover five such additional identities from specific-entity death
  and specified-entity trigger events, while explicitly rejecting kickable
  leave-trigger output as a non-alias. Four otherwise-unplaced world identities
  are exact NPC proxy placements through matching registry segment key,
  unique proxy-table row, identical finite position, and authored rotation.
  The remaining 53 identities / 77 constant references stay non-spatial.
  All 1,840 NPC proxy points now participate in the same observational action
  audit under an explicit NPC identity domain. A pinned `NpcProxyGetter`
  contract resolves 14 exact getter-backed action fields to eight unique NPC
  points;
  the report retains the selected getter slot, proxy lookup, native contract,
  and exact registry/table placement chain. The formerly unresolved
  `NpcEnableStim`, `NpcPatrolOverrideGait`, and
  `SetEntityEulerAnglesLookAt` fields are pinned formatter members, so all
  seven corresponding references across six NPC points are exact. Of the
  serialized dynamic fields, 28 now resolve to an actually published spatial
  action, 494 are native-validated runtime non-spatial values, and 1,884 remain
  unresolved. Nineteen of the runtime non-spatial rows have an exact
  `LevelScriptBriefData` type-13 EntityPtr initializer and matching authored
  registry position, but the native lifecycle proves that the source-200
  blackboard remains mutable after binding; they are published as non-final
  diagnostics and never promoted to action targets. Resolved spatial rows stay
  in the full field diagnostics but no
  longer appear in `unplacedDynamicReferences`.
  Every retained unplaced dynamic row now carries a bounded resolution failure
  gate. Exact null EntityPtr getter values, native non-aliases, runtime list
  elements, mutable initial properties, named runtime arguments, and missing
  authored spatial identities therefore remain distinguishable instead of
  collapsing into one generic unresolved class.
  `RepeatEntityPtrListAction._entity` accounts for 461 of the validated
  non-spatial rows: its pinned execution path selects an entity from a runtime
  list rather than aliasing a serialized constant. Spawner and other event
  outputs are separately classified as runtime-produced diagnostics, but stay
  unresolved unless their exact native producer semantics are contracted.
  Pinned native consumers prove that current-script EntityPtr resolution uses
  `ActionContext`'s LevelScriptRuntime script id plus EntityManager's live
  `(scriptId, slotId) -> logicId` dictionary; LevelInteractiveData is not in
  that lookup. A unique aligned WorldEntityRegistry script/slot row therefore
  proves the authored offline target and transform without requiring a second
  LevelInteractiveData match. It does not prove that the entity was registered,
  initialized, or alive when the action executed, so every such action retains
  `runtimeLifecycleStatus: unproven`.
- Mission selection no longer suppresses exact missionless level-world rows.
  Compact maps expose all recovered types initially; the current e0m0 view
  visibly includes five authored grenade towers, one enemy, four tomb scenery
  props, travel poles, triggers, and the Story reading point. The tombs now
  carry their exact LevelData NarrativeComponent bindings:
  `8700020001 -> misc_dlg_e0m0_0d5`, `8700020002 -> misc_dlg_e0m0_0d9`,
  `8700020003 -> misc_dlg_e0m0_0d8`, and
  `8700020004 -> misc_dlg_e0m0_0d7`. Each edge comes from one counted
  LevelInteractiveData record containing both `embeddedLogicId` and `typeId`,
  not entity-number order or spatial proximity. Grenade-tower
  semantics are backed by exact FactoryBuilding, FactoryBattle, and Model rows.
  Enemy markers use localized EnemyTemplateDisplayInfo names, and exact reading
  points use their generated Story title (for example `text_e0m0_1` is shown as
  `墓志铭`). The remaining e0m0 `int_empty` rows are published in a separate,
  default-hidden unresolved-empty-slot layer with `empty_interactive_shell`
  status; no unsupported interaction role is inferred from an empty definition.
  LevelScript ownership and
  script-wide condition/order context no longer fan out across every sibling
  slot; point-level Story/file links require an exact script/slot consumer.
  Registry evidence opens as an identity-focused highlighted excerpt: world
  ids address `worldEntityBriefInfos`, while script id/slot pairs first resolve
  their shared index in `m_scriptEntityIdList` and `m_scriptEntityBriefInfo`.
- The resizable left rail is a three-column map/task/object-filter tree; its
  task column owns the map status formerly shown in a top panel. The plain
  third column combines object and render-layer filters without a disclosure
  header, nested layer container, separate bottom dock, or inner column
  scrollbars. The resizable right
  inspector retains complete node fields and raw JSON/file access. Unnamed single-mission maps inherit that mission's
  localized code/name. e0m0 explicitly links from `indie_dg002` to its
  `indie_dg004` ending scene; trigger-volume slots without a recovered world
  transform remain visible unresolved evidence.
- Map-wide files and weak file associations are hidden in the normal inspector
  unless their path resolves to an exact Story deep link. Debug mode restores
  the complete evidence inventory and turning it off closes a now-hidden file.
- The two physical `O.M.V.帝江号` levels and the main/guide `谷地像差` levels
  are collapsed into one place each in the map column. Their variants remain
  explicit task-column items and load their own payloads. `谷地像差` now uses
  its exact streaming render by default while retaining the inferred HLOD as
  diagnostic evidence. The six published danger-reappearance maps expose a
  concise surface-accuracy grade without hiding their detailed JSON.
- Static projections may omit explicitly named roof/ceiling instances for a
  documented cutaway. Material color is used only with an exact, unique
  mesh/material/base-texture/UV closure; those recovered texture samples keep
  their source RGB in surface and point output instead of receiving synthetic
  height darkening. Unbound pixels retain the established colored elevation
  fallback so the material/surface layer stays readable; exact bound samples
  continue to take priority over that fallback.
- Map01/Map02 default to loading the selected zone only. The bottom-centre
  range control explicitly opts into every Wuling or Valley-IV member and
  releases sibling payloads again when returning to the single-zone scope.
- Water coverage requires authored minimap pixels plus exact WaterData scene
  evidence. Flowmaps remain corroboration only.
- e0m0's generated HLOD naming contract now supplies a material closure: every
  published cluster must uniquely match a generated material by exact
  level/LOD/signed suffix, and the material must own one `_BaseColorMap`
  PathID. The resulting surface and point layers are textured base-color
  diagnostics; game lighting, fog, exposure, tone mapping, and grading remain
  unrecovered and must not be approximated with a global color correction.
- That exact generated-material closure now covers all published HLOD maps and
  source-art dungeon crops, rather than being limited to e0m0. The current
  index resolves every cluster uniquely; future missing or duplicate keys fail
  closed. Streaming meshes still require exact ordered Renderer material PPtrs
  before normalized-name gaps or multi-material submeshes can be recovered.
- Ordinary streaming scenes now apply the same exact level/LOD/grid/cluster
  HLOD key used by Map01/Map02. `indie_dg002` therefore retains its large HLOD
  environment through original InitChunkData matrices while unresolved keys
  remain omitted; this replaces the former local-static-only projection.
- HLOD point output preserves every deduplicated projected vertex in a sparse,
  deterministic height sidecar. Partial height filters select the highest
  in-range sample per pixel, while the existing top-point PNG remains the
  full-range fast path; upper-layer removal therefore exposes lower geometry.

Evidence boundary:

- Coordinates and matrices prove placement, not runtime activation,
  interactivity, visibility, prefab identity, or renderer ownership.
- Current-build GameAssembly confirms that map UI positions and lengths use a
  single linear `world / gridWorldLength * gridRectLength` conversion;
  `InverseUILevelMapPosition` only swaps axes and negates one axis. The same
  build's `DynamicSceneUtil.GetGridSizeByLen` starts at 32 m and doubles per
  encoded grid level; the exported HLOD index ranges halve at each adjacent
  HLOD, establishing HLOD0/HLOD1/HLOD2 as 32/64/128 m rather than the former
  hand-derived 64/128/256 m assumption. Map01/Map02 no longer use that grid to
  publish geometry: their original region `InitChunkData` contains HLOD entity
  names plus complete 4x4 matrices. The maintained recovery joins a matrix to
  an exported Mesh only when level number, HLOD level, grid i/j, and signed
  cluster hash all agree exactly. Normal map alignment uses those matrices and
  authored `UILevelMapLoadConfig` rectangles with no presentation transform;
  missing joins fail closed. Exact HLOD surface output retains the joined
  geometry. Material and grayscale elevation layers retain that full surface;
  only the sparse point layer excludes named structural meshes and broad
  near-horizontal non-prop slabs. The point layer is a
  deterministic world-space surface sample controlled by
  `--surface-point-density` in samples/m2; density affects presentation only.
  Maps without minimap art retain an exact registry/quest-transform point
  fallback when inferred HLOD placement is suppressed.
  Exact authored HLOD GameObject/Transform records remain unrecovered.
- Story producer/slot, NPC proxy, and authored map-pin joins remain distinct
  from script-condition, proximity, mission-area, and quest context.
- Generated counts and per-build inventories belong in
  `reports/assets/map_recovery/`, not this file.

Highest-value gaps:

- Recover exact scene hierarchy and renderer ownership where HLOD or
  InitChunkData currently proves only geometry/placement.
- Recover water-surface geometry for scenes without sufficient authored map art.
- Add behavior-level frontend coverage if a maintained browser test harness is
  introduced; do not restore source-string snapshot tests.
## Updates and packaging

```bat
.\build_updates.bat OLD NEW
python scripts\pack_webui.py
```

Updates compares complete saved/current export roots only. The default feed
covers WebUI-facing exported text plus image, model, video, and decoded audio
assets. Local WebUI, report, memory, and scratch changes are excluded.

## Highest-value gaps

- Keep optional semantic sidecars visibly degraded rather than silently stale.
- Improve exact Gameplay-to-asset and sound ownership without weakening labels.
- Preserve clear evidence boundaries as Mission Pipeline gains runtime joins.
- Recover exact `indie_dg002` scene Transforms and use them to validate or
  replace the current inferred HLOD grid preview.
- Keep Characters false-positive exclusions and live overrides clean.
- Maintain accessible behavior across large Story, Gameplay, Audio, and Assets
  datasets.

## Verification

1. Run the smallest relevant builder after confirming export freshness.
2. Smoke-test all normal pages and debug-only Mission Pipeline routing.
3. Verify Story reset, issue/method filters, and SNS media fixtures.
4. Open representative playable and enemy entries; check variants,
   progression, skills, projectiles, sound, and asset links.
5. Check console errors and explicit degraded states.

Changing inventories and schema-specific counts belong in generated reports,
not this file.
