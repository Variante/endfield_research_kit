# WebUI recovery

## Current status

The static WebUI is the project’s primary surface. Story, Characters, Gameplay,
Audio, Assets, Text, and Updates are normal pages. Mission Pipeline is
experimental and appears only with `Show debug info`; Audio and Mission
Pipeline retain visible under-construction labels.

Story, localized references, character identities, gameplay semantics, assets,
audio, and update comparisons build reproducibly from a current
`export_full/`. Optional datasets fail visibly when absent or stale.

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
the filename. Its playable-media section is placed immediately below the
Details heading, before manual notes and evidence facts, so the player is
available near the start of the detail pane. These annotations are user
research state and do not upgrade or modify generated evidence.

Audio separates Event/media identity, Wwise graph relation, authored consumer,
and observed runtime execution. A stronger layer never appears unless its typed
evidence exists.

The current pipeline can join raw HIRC Events, decoded media, AudioDialog and
responsive-voice tables, Timeline audio, Lua consumers, selected serialized
components, gameplay actions, and fingerprint-locked native callsites. Direct
and conditional native consumers retain their method, callsite, target, and
branch evidence. Selector and dictionary paths stay distinct from direct
literal playback.

Missing or mismatched installed native inputs never erase authored Audio rows.
They suppress only build-locked callsites/mappings and expose a bounded
unavailable diagnostic, so the page cannot silently present stale native
addresses as current evidence.

ModelView normal Event contexts show the authored controller/model/layer/state
chain and `behaviorTime` with explicit labels: `Authored`, `static route`,
`runtime unobserved`, and `branch unresolved`. The static route is shown only
for the fingerprint-locked `AudioBehavior.Execute` -> `AudioManager.PostEvent`
contract; execution, branch choice, and audibility are not inferred. The
runtime overview publishes no `nativePairing` unless a complete
hash-verified closed capture session exists; partial key/path/handle/decoder
overlaps remain unobserved.

Positioned ModelView audio shows three authored branches. Only a direct-position
Event with nonzero `normalAudioId` exposes Event/media candidates. Its managed
Adapter route, managed internal playing id, and `LoadBank`/`PrepareEvent`
boundaries are static evidence; runtime-dynamic completion, final
`AkSoundEngine.PostEvent`/native playing-id handoff, Wwise selection,
execution, and audibility remain unresolved. Custom and entity forms are
control-only; `_SwitchState` has no recovered playback sink, and neither form
promotes an Event, media leaf, or owner.

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
The only current CN media row with `purposeKnowledgeStatus=unknownUse` is
`au_voice_c35m3_3_001` (`v1d4/Narrating/HS_Part04/c35m3/...wem`). The source
graph confirms only its decoded-file and recovered external-identity edges;
there is no AudioDialog, Story-line, or trigger-context edge. The `c35m3`
chapter-like path is identity/evidence context, not a recovered playback
trigger, so the row remains an explicit highest-priority recovery gap.
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
live branch observation. In a selected Audio record, playable media is shown
immediately under the detail heading, ahead of the longer facts/evidence list.

## Story and Mission Pipeline boundary

Story combines authored dialog structures, Timeline placement, mission/runtime
links, localized references, and manual order without flattening their evidence
types. Cutscene shapes, subtitle evidence, definition-only media, authored
placement, and runtime activation remain distinct.

Mission Pipeline shows typed trigger chains and their ownership/activation
gaps. Native registration, source order, code address, proximity, OCR, and
manual order never become mission chronology by themselves. Weak placement is
visually separate and cannot override exact placement.

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
