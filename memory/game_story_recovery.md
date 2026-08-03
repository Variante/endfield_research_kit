# Game Story recovery

## Current status

The client supports a useful evidence-backed partial order, not one complete
canonical scene list.

Latest CN reports:

| Metric | Current |
| --- | ---: |
| Pipeline missions | 605 (490 MissionRuntime + 115 Story-only recovery shells) |
| Unique Story files | 5,564 |
| Connected files | 4,239 (76.2%) |
| Files with a normalized trigger/context route | 4,462 (80.2%) |
| Unlinked files | 1,325 |
| Unlinked files with exact native playback | 156 |
| Encounter-controller contexts | 5 receiver scripts / 7 modules / 27 Story keys / 9 related source files |
| Exact non-mission content | 281 (280 spacecraft/profile + 1 guide runtime) |
| Actionable core-isolated files | 0 |
| Partial-order mission rows | 487 |
| Candidate scene placements | 8,877 |
| Strong / supported / weak edges | 1,502 / 834 / 2,635 |
| Exact native Story transitions | 380; 85 branch-bearing across 40 missions (77 Split, 7 conditional, 1 ordered-sequence) |
| Source-comparable scene pairs | 3,791 / 249,695 (1.52%) |
| Cyclic components | 0 |
| Exact nested DialogTree containments | 49 across 44 child files |
| Exact quest-observed DialogTree definitions | 434 definitions / 461 placements across 422 quests |
| LevelScript action topology | 4,512 / 4,512 classified; 0 fail-closed |
| Native branch predicates | 258 named; 263 semantic including 5 inline; 0 class-only; 0 unresolved |
| Exact receiver playback gates | 30 Story files (15 Boolean comparisons, 6 NOT, 4 integer equalities, 2 AND, 1 OR, 1 ALL, 1 Boolean leaf) |
| Exact post-playback control | 128 graphs / 105 Story files / 348 actions and edges / 18 branch points / 76 unresolved server handoffs |
| Exact post-playback LevelSequence files | 15 typed action placements / 7 serialized ids / 6 exact original TextAssets / 1 unresolved root handle |
| Post-playback variable bridge | 23 typed setters / 50 exact listeners / 0 same-level, same-script, same-key joins |
| Binary-proven cinematic producers | 10 native producers / 16 typed action routes / 1,682 route attachments across 1,332 Story files |

Persistent `MissionRuntimeAsset` is the effective authored corpus only when it
contains the complete StreamingAssets filename set; otherwise builders use the
whole StreamingAssets corpus. The current roots share 980 filenames and differ
in five payloads.

## What is recovered

- Mission and quest graphs, predecessor relations, forks, and merges.
- Story cards for dialog, radio, SNS, cutscenes, black screens, and remote
  communication.
- Typed LevelScript, DialogTree, Timeline, FMV, quest-state, interactive, and
  selected runtime receiver evidence.
- Exact native control paths for Split, If/Else, Switch, ordered Branch, playback, and
  many event families.
- 307 native branch groups and 19 native convergences, kept as a partial
  graph instead of flattened into a guessed file list.
- All 3 previously opaque native branch predicates are now typed from the
  current binary: one general LevelScript-stage comparison and two instances
  of the general mission-or-quest completion getter.
- All 7 formerly class-only predicates are now operand-decoded by two general
  serializers: six `GetConditionResult` records reuse the root
  `GameCondition` union decoder, and one `IntEqual` accepts the formatter's
  polymorphic constant/local-getter operands.
- 368 strict option-route groups covering 767 option arms and 1,597 branch
  lines.
- Source-only graph generation with zero cycles and explicit unknown pairs.
- 180 of 188 narrative-video references attached across 53 Story keys.

The registered DialogTree trunk-group recovery handles complete, partial, and
row-reuse emitted shapes with fail-closed content-identity rules. Mechanical
`misc_*` aggregates select their authored prefix namespace; direct unregistered
`dlg_*` scenes select only exact `<scene>_<digits>` rows, preventing a shorter
key from absorbing nested scenes such as `_1_2`. Each covered row must belong
to exactly one current registered, hash-validated serialized DialogTree;
duplicate carriers resolve only through the existing namespace tie-break, and
naming never fills a missing row. Complete partitions include the speed-limit
scene through its exact registered `_1` parent. Five partial scenes span ten
parents: 30 of 38 authored rows are covered and eight are explicitly
unmatched. A complete literal census checks every unmatched row against all
decoded registered DialogTrees, all 4,512 exported LevelScripts,
`GameAssembly.dll`, and `global-metadata.dat`. The rows occur in none of those
consumer surfaces, so they remain current table definitions without consumers
and are never appended to a neighboring parent. The separate two-digit
`dlg_blackbox_shaper_2_2` group is an exact table-only definition; suffix width
is authored data rather than a classifier constant. A general parent-namespace
resolver now attaches an exact authored
level/dungeon asset shell only when `LevelBasicInfoTable`, the unique
`DungeonTable.sceneId`, LevelConfig, the 43-member LevelData MemoryPack, and any
matching decoded map TextAsset all independently name the same level. It
publishes 40 contexts for 37 complete groups and eight contexts for the five
partial groups, including every related LevelConfig/LevelData file and map
TextAsset PathID/hash. The general resolver now continues through the exact
`BlackBoxSubGameData` row and `bindScriptId` into the bound LevelScript. It
keeps `mainTasks`, `extraTasks`, and `failTasks` as separate authored SubGame
lanes and attaches only exact typed `StartDialogAction` playback for selected
parent DialogTrees. A single current-build decoder, keyed by the audited
GameAssembly condition-union tags and the installed metadata formatter setter
order, now recovers all 50 available bound BlackBox task maps: 49 complete maps
and one authored null map. Across the 46 maps on the registered DialogTree
recovery surface this yields 327 tasks and 542 conditions with zero validator
failures. Exact nested `ScriptTaskExtraInfoTable` rows attach objective display
keys; `CombineCondition` formulas retain their authored operands. The task
dictionaries contain no task-successor or Story-file-order field, so the
topology remains objective structure rather than chronology. All eight partial
level contexts have an exact parent playback. Pipe 1 plays `_1` from its bound script while
`_2` and `_3` remain explicitly definition-only there; this partial coverage
is preserved instead of forcing one uniform producer rule. Numbered
missing-row positions remain table-row cross-reference diagnostics only. These
relationships remain graph-neutral and do not place the eight loose rows.
A second general decoder follows only the serialized action-map membership,
`ActionHeader.nextId`, `ActionBase.nextId`, and typed control fields recovered
from the current GameAssembly formatter and Execute bodies. Current
`Branch.Execute` at `0x18764d990` reserves itself and advances `_idList` one
item at a time, so `Branch.sequence[*]` is ordered iteration, not fan-out;
`Split` is parallel fan-out, If/Else and Switch select one arm, and While is a
loop. Zero action ids are exact terminal pointers. The current binary also
proves one reusable construction rule for all three `ActionMapRuntime`
collections: serialized header, action, and getter records are assigned into
their respective runtime arrays by local id, so the final serialized record
for a repeated id is active and earlier physical records are runtime-shadowed
audit rows. Event roots are resolved by indexed header id and invoked
independently; physical header-list order and listener priority do not provide
Story chronology. The current 13,458-header census has no repeated header id,
while getter indexing exposes 120 shadowed physical rows. Listener metadata is
overwhelmingly priority `0` (13,455 rows), with three `-1000` spawner-death
listeners retained as metadata rather than order evidence. If
a positive continuation has no active slot, `ActionExecutor._DoLogicTick`
removes an invalid stack layer or calls `_NormalReachEnd`; it is an exact
terminal, not an unparsed object. The 4,512-file census now classifies every
file: 522 authored empty maps, 487 files with no map, 3,403 ordinary complete
maps, and 100 complete maps with action-slot runtime shadowing. Across 49,127 physical
action records, 48,712 active slots remain; 415 records are shadowed across
242 repeated ids (26 ids change payload), and 23 missing-slot terminals occur
in 14 files. There are zero fail-closed graphs. It contains 81 ordered
sequences, 2,786 Split fan-outs, 2,549 conditional selectors, and 29 loops. On
the current BlackBox recovery
cards, 47 complete graphs contain 718 actions, 147 event roots, 719 edges, 16
ordered sequences, zero fan-outs/conditional selectors/loops, and one event
entry convergence. Separate event roots still have no serialized relative
order. The five unresolved-row families contain no action fan-out and
their typed playback targets only the already registered parent DialogTrees;
none targets the eight loose row ids. Mission Pipeline displays the SubGame id,
bound script, task topology, condition families/formulas, objective display
keys, the complete event/action graph with semantic control kinds and Story targets,
definition-only parents, sources, and boundaries in visible Story-only shells.
The source partial-order report attaches 1,516 compact original LevelScript
graphs across 221 rows only when an exact native event-to-Story path already
relates the file. Mission Pipeline publishes the 1,439 attachments whose 202
missions have WebUI shells. Each attachment retains its selected active event
listener, listener metadata, physical/active counts, shadowed slot counts, and
the shared original-binary runtime mapping; the rest of each graph stays
file-local context.
The same general path-prefix recovery now preserves the complete typed action
suffix for all 380 exact native Story-to-Story transitions rather than reducing
the proof to local-id lists. Eighty-five transitions in 40 missions traverse a
typed non-linear edge: 77 cross `Split.actions[*]`, seven cross an If/Else or
Switch arm, and one enters `Branch.sequence[1]`; every transition also retains
its linear steps. Mission Pipeline renders the source and target Story files,
each exact successor field, decoded branch predicate when available, and all
related original LevelScript/MissionRuntime files. This does not add or promote
an edge—the same 380 path-prefix relations were already strong—but makes their
branch semantics and provenance directly auditable without consulting OCR,
manual order, record adjacency, or filename numbering.
The current PureGetter and root `GameCondition` union registrations, generated
MemoryPack setter order, and native `GetResult` bodies close all ten formerly
opaque or class-only branch predicates without mission-specific rules.
`CheckLevelScriptStage` decodes its
comparer, LevelScript pointer, and expected stage; the present `e7m3` record is
`current script stage Equal 0`. `CheckMissionOrQuestIsComplete` decodes its
mission/quest selector and serialized identity; the present `sm1l1m2` and
`sm1l2m4` records test quests `sm1l1m2_q#7` and `sm1l2m4_q#8` for the native
completed state. `GetConditionResult` embeds a root `GameCondition`; the six
current branch records decode as `CheckFMVFinish`, `CheckServerGlobalVar`, two
`CheckLevelScriptPropertyInt`, `CheckLevelScriptPropertyBool`, and
`CheckClientGlobalVar`. The remaining `IntEqual` reads local getter `#183`, an
authored `IntGetterRandom` over 0–2, and compares it with constant 0. Mission
Pipeline renders those nested fields, getter linkage/range, both branch arms,
and the exact LevelScript source file. Payloads must consume exactly, apart
from the already proven outer action-map trailer, so changed or malformed
shapes remain unresolved.
The current original binary also identifies one reusable non-owning receiver
family: `EncounterBase<T>` owns the enabled/activated/completed/failed,
battle-completed, and first-intro lifecycle properties, while `EncounterData`
owns the enemy-list and typed spawner fields. A structural classifier requires
all eight exact module-prefixed properties and their native value shapes; it
does not inspect host, Story, or object filenames. Installed
`LevelScriptModule.GetSaveKeyPrefixed` reads the LsmPtr module id from
`this+0x18`, proving that this namespace may differ from the receiver
LevelScript id. The current census recognizes seven modules across five
receiver scripts and 27 Story keys. It attaches five validated receiver-host
placements across three distinct LevelData files, plus the six existing
SpawnerConfig files named by positive typed `spawner_id` values; the seventh
contract has the valid zero/no-spawner form. Five module ids differ from their
receiver script id. Encounter activation still supplies no MissionRuntime
foreign key, Story branch, or order edge.
The same receiver surface now follows the general serialized
`ActionHeader._validate` parameter into its ActionMap getter rather than
special-casing Story ids. Installed `ActionHeader.DoProcess` reads the Boolean
parameter through `Param<bool>.get_useGetter` and `ParamExtensions.GetValue`
before proceeding. Of 30 receiver headers with local validation getters across
20 LevelScripts, all 30 now consume fully decoded predicates through one
recursive getter-graph resolver: 15 Boolean comparisons, six NOT, four integer
equalities, two AND, one OR, one counted ALL, and one direct Boolean leaf. The
resolver follows typed local-getter references, selects the active final
serialized runtime slot, and fails closed on unknown, missing, cyclic, or
malformed children. Installed `BoolGetterAnd`, `BoolGetterOr`,
`BoolGetterInvert`, and `BoolGetterMultiAnd.GetResult` bodies prove the logical
operations; `GetterBool`, `GetLsmIsCompleted`, and `InteractiveCheckState`
formatter fields and consumers prove the remaining leaves. The eight
`indie_dg002/8700050001` radio gates are exact `*Played == false` checks. The
newly exposed compound gates include property/stage expressions, one LSM
completion inversion, and one six-child interactive-state conjunction. These
are receiver-local allow/block branches only: they do not
prove a post-play server write, mission ownership, or order between Story
files.
The identity-agnostic control decoder now also publishes typed successors after
any exact receiver Story action instead of truncating the visible path at
playback. The current unresolved receiver surface contains 128 exact
post-playback graphs across 105 Story files, with 348 unique local actions and
edges, 18 typed branch points, and 76 `CallServer` handoffs. Mission Pipeline
renders maximal reachable paths, branch points, callback correlation labels,
and the original LevelScript file. Callback labels identify neither a server
handler nor a mission/quest or state write. For `cutscene_e3m5_4`, the exact
client path is now visible as `isFinished == false` -> FMV -> fade-in ->
`CallServer #27b725be`; the separate `e3m5_q#1` objective observes the same
LevelScript property, and its original Persistent
`MissionRuntimeAsset/e3m5.json` is attached as a related file. This still does
not prove that the quest starts playback or that the handoff writes
`isFinished`, so the Story remains unowned.
The same general action-family projection resolves original LevelSequence files
without a sequence-id allowlist. Action class names come from the installed
`ActionBaseForMemoryPack` formatter table; this additionally identifies union
tag `0x02fa` / 9 members as `LoadLevelSequenceAction`. A candidate action text
joins only when the exported TextAsset's `m_Name` and `Name` and its decoded
`m_Script.cutsceneName` are all exactly equal. On the current receiver surface,
15 typed action placements carry seven serialized ids; six ids resolve to six
original TextAssets across ten placements. The remaining
`levelseq_e11m1_dg011` is retained as an unresolved root/control handle rather
than expanded by name. The complete 400-file source census admits 399 exact
identities and fails closed on
`levelseq_map01_lv007_CM_pC5E4AF1F6301DEFF.json`, whose internal
`cutsceneName` is `cutscene_c33m1_1`. Mission Pipeline shows each matched file,
PathID, action type, unresolved id, and the bounded validator diagnostic. These
links are local cinematic context only and add no mission owner or Story-order
edge; OCR and manual order are not consulted.
The complete current-build native playback index now also feeds one general
post-playback variable-bridge audit. It discovers setter and listener classes
from their exact serialized contracts, extracts keys without Story/object-name
rules, and joins only `(levelId, scriptId, key)`. Across 3,188 native Story keys
and 3,816 playback occurrences, 23 typed post-playback setters (`SetInt`) and
50 exact listener rows (38 property, 12 blackboard; 33 unique selectors) have
zero joins. The installed formatter and metadata prove the key/value and
listener payload shapes; the generic `Set<T>.Execute` body is unavailable in
the current native body table, but the zero overlap closes this route without
assuming which notification family it emits. It therefore creates no
ownership, branch, or order edge and uses neither OCR nor manual order.
No current mission has Story targets on two different Branch sequence slots,
so there are still zero Story-to-Story edges derived from relative sequence-slot
indices. One existing path-prefix edge enters `Branch.sequence[1]` after its
source Story and now exposes that typed suffix without claiming a second Story
sequence arm.
The actionable core-isolated queue is empty and the current contract is
`sourceStoryGapQueue.v130`; OCR and manual order remain comparison-only. The
queue now loads the current Story trigger manifest through an exact schema,
language, source-hash, and object-shape gate instead of silently discarding a
newer coverage schema. General closure contracts revalidate shipped-Lua
`GameAction.<method>` calls against their matching native entry and exact
Lua/audit hashes, and revalidate composed CutsceneRoot playback aliases against
their independently connected native route. This closes the former top
false-positive gaps `cutscene_e1m10_1` and `cutscene_gm02m4_1` without adding
ownership or chronology edges. Validator drift now reports the mission, Story
key, failed gate, bounded expected/actual values, source paths, and hashes.
The same trigger-manifest layer now preserves `sourceFile`, native event,
mapping, carrier, PathID, and typed quest-gate fields generically. Separate
fail-closed relation contracts close `dlg_sm1l1m1_16` only from its exact
quest-owned reachable DialogTree carrier and `radio_f1m5_2` only from its
serialized leader-volume -> `CheckQuestState(Equal, Processing)` ->
`PlayRadio` chain. Arbitrary Story ids using either shape are supported; the
multi-quest DialogTree branch subtype remains separate. Both closures retain
source hashes and quest context but add no relative Story-file edge.

The latest batch removes two object-shaped blind spots with reusable negative
consumer rules. Mechanical `misc_dlg_*` aliases now enter the same exact
DialogText/DialogOption/audio, registry, Timeline, typed action/playback,
object-carrier, GameAssembly, and metadata exhaustion gate as `dlg_*` roots;
option-group tokens may be alphanumeric. This defers surviving table-only rows
generically, including both `sm1l5m3` `0d5`/`4d5` definitions, without turning
options into routes. Typed spaceship trees now establish actor/family contexts
from carried line ids; a complete sibling DialogText bucket is deferred only
when no related typed tree carries any target line. That rule finds exactly the
two gift `recvbye` buckets, attaches their four related original DialogTrees
plus `DialogTextTable`, and leaves playback, ownership, and chronology unknown.
Together these rules reduce other-bucket actionable core rows from 30 to 13;
main, event, major, and character remain zero. The partial-order graph is
unchanged.

The latest cutscene batch removes the remaining root/director shape blind spots
with two reusable identity rules. A typed `CutsceneRootComponent` normally
identifies its Story root through `_timelineName`; when that field is a runtime
`levelseq_*` token, the reverse-PPtr audit accepts the exact root GameObject
name only if the component is on the hierarchy root, the name is a current
Story key, and no scalar Story key resolved. Five current director hosts use
this fallback. This closes `cutscene_map02_lv001_TSZ_01_3_copy` through its
exact `_director -> PlayableDirector -> m_PlayableAsset` chain. A separate
general pair classifier recognizes an exact cross-key root/playable alias only
when both registered TextAssets round-trip through the Timeline dictionaries,
the root object graph and played asset graph are complete, the current binary
tokens/typed playback/carrier surfaces remain absent, and the unique pointer,
containment, and mission sets agree. It closes `cutscene_f1m9d3_1` as the root
definition and `cutscene_f1m9d4_1` as the played TimelineAsset. Both Mission
Pipeline cards attach the exact TextAsset, registry tables, object audits,
installed binary/metadata, and the two original VFS chunks. The alias proves
playback composition only; it does not order `f1m9d3` against `f1m9d4` or
identify either mission activator. The actionable queue falls from 13 to 10;
main, event, major, and character remain zero, and the graph remains 1,502
strong edges, 265 forks, 55 merges, 307 native branch groups, and 19
convergences.

The original metadata `BlackboxGuideHintController`, `FacGuideHintEnable`, and
`LevelDataGuideHintConfig` surface is spatial factory guide-hint configuration,
not DialogText playback. Exact current LevelData strings and typed members do
not consume the eight unmatched rows, so this path is excluded rather than
used as a naming-based attachment.

A separate generalized carrier layer removes the object-specific parent-dialog
dependency catalog. A focused parser resolves one current registered
DialogTree and re-derives every exact prime-reachable trunk or nested-dialog
carrier from its serialized nodes and connections; the validator compares the
complete carrier paths and fails closed on current registry, source, PathID, or
hash drift. This
general rule closes six dependencies, including uncatalogued `dlg_f1m10_8`,
`dlg_f1m10d1_5`, and `dlg_f1m28_5`. Two further typed NpcProxy navigation and
lazy-destroy relations now compose an exact registered DialogTree definition
with current `GameAssembly.dll`, MissionRuntime, proxy-table, and world-registry
evidence without claiming playback ownership. NpcProxyEx rows shared by
multiple mission contexts retain the complete authored context set as
alternatives, never chronology. Mission Pipeline publishes localized
graph-neutral cards for these relation families, including context/quest sets,
source files, hashes, and binary boundaries.

The same registered DialogTree trunk-group rule was first applied to mechanical
`misc_timeline_*` aggregates. An aggregate closes only when its complete current
`DialogTextTable` namespace is an exact one-parent-per-line partition across
registered, hash-validated `Beyond.Gameplay.DialogTree` assets. Original
serialized connections retain exact internal line order and branch counts;
current `GameAssembly.dll` consumers prove typed trunk playback, but neither
activation nor order between separate parent roots is inferred. When two exact
registered carriers duplicate the same lines, the authored
`timeline_<family>` to `dlg_<family>` namespace convention is used only as a
tie-breaker; it cannot fill missing rows. `misc_timeline_blackbox_miner` and
`_pipe` remain open because authored rows lack serialized registered owners.
Mission Pipeline exposes the parent files, hashes, and directed edges.
Canonical mission-pipeline builds refresh and validate
`sourceStoryGapQueue.v129` after current Story coverage
and partial order are published; data-only builds deliberately reuse it. OCR
and manual order remain comparison-only.

The preceding recovery batch generalizes two cross-owner context patterns without
reassigning Story ownership. A typed quest-state `PlayRadio` path may retain its
foreign mission, quest, LevelScript, and original GameAssembly action mapping
when every current-build occurrence agrees; this closes
`radio_m1m10_{8,9,10}` through the exact completed-quest paths in `m1m16`,
`m1m17`, and `m1m18`. Typed DialogTree narrative-mask actions now retain their
exact parent dialog and every exact parent LevelData playback shell; this closes
`black_sm1l2m2_0d5`, `_2`, and `_3` through `dlg_sm1l2m2_{5,10,11}` while
preserving the foreign `sm1l2m1` shell. The stricter carrier scan also disproved
three hard-coded TextTable-only classifications: `black_e7m1_3` has exact native
event playback and `black_e11m8_12`/`_39` have typed DialogTree carriers, so the
object-specific negative overrides were removed. Both validators fail closed
with bounded source/hash diagnostics. Mission Pipeline exposes the quest,
parent-dialog, LevelScript, LevelData, and TextAsset files; the gap queue moves
from 79 to 72 actionable files, with `m1m10` and `sm1l2m2` both at zero. These
relations have `graphEffect: none`; the graph remains 1,502 strong edges, 265
quest forks, 55 merges, 307 native branch groups, and 19 convergences. OCR and
manual order remain comparison-only.

The preceding recovery batch generalizes typed system Story selectors instead of
adding an `f1m25` exception. `DomainDepotConst.depotDeliverMissionId`, the
dialog-table key/`npcProxyId`, and delivery-target `targetId` form an exact
typed join; current GameAssembly consumers prove that the delivery response
installs and later removes the selected dialog override. The generic carrier
publishes each same-row selector as graph-neutral alternatives with authored
roles and fails closed when the mission, role/key set, sources, native mapping,
or order boundary is incomplete. For `f1m25`, this exposes 12 NPC-target
groups covering 24 `initialDialogId`/`repeatDialogId` files and attaches all
six Persistent/StreamingAssets table sources in Mission Pipeline. The queue
falls from 103 to 79 other-bucket actionable isolated files; `f1m25` falls
from 24 to zero with 24 exact selector closures and zero validator failures.
It deliberately adds zero Story-order edges: the binary evidence does not yet
prove initial-before-repeat chronology or an order between delivery targets.
OCR/manual order remains comparison-only.

The preceding recovery batch generalizes spacecraft/operator content recovery
without actor- or file-specific rules. Complete DialogText buckets close only
when an exact typed `DialogTree` consumes every line through
`SpaceshipOptionGiftData` or `SpaceshipOptionWorkData`, or when a mechanical
`CharacterTable.profileVoice` mirror has an exact duplicated `AudioDialog`
metadata pair. Current GameAssembly and metadata hashes pin the reviewed gift,
work-state, dialog-selection, and NPC reaction consumers. This classifies 280
non-mission Story keys: 194 typed DialogTree buckets (138 gift, 28 rest, 28
work), 84 profile-talk buckets, and two current-build unconsumed gift
definitions. Mission Pipeline exposes the exact
non-mission records in one collapsible browser with their original DialogTree
and table files. The two `recvbye` rows remain explicitly absent-carrier
definitions rather than being promoted to playback.
These classifications prove content and internal branch membership, not mission
ownership or cross-file chronology; OCR/manual order remains comparison-only.

The preceding recovery batch generalizes exact LevelData-hosted LevelScript
playback across matching and foreign mission shells. The validator requires a
typed current-build playback action, exact native event-to-action path,
GameAssembly mapping, complete single-key authored record, mechanical
`misc_dlg_* -> dlg_*` alias where needed, and a validated
`LevelData/43.member22` script dictionary host. Mission equality changes only
the displayed ownership boundary; it is not a separate per-mission rule. This
closes `misc_dlg_e1m3_5d5`, `misc_dlg_e6m3_3d5`,
`misc_dlg_f1m9d1_4d5`, `misc_dlg_f1m9d3_3d5`, and
`misc_dlg_sm1l3m1_1d1`. Main, event, major, and character buckets now have
zero actionable core-isolated files; the other bucket falls from 384 to 381.
Mission Pipeline shows a localized exact-playback boundary plus both original
LevelData/LevelScript files. No quest trigger or relative order is inferred,
and the graph remains 1,502 strong edges, 265 quest forks, 55 quest merges,
307 native branch groups, and 19 native convergences. OCR/manual order remains
comparison-only.

The preceding recovery batch closes all eight remaining quest-to-Story attachment
gaps with schema-driven rules rather than quest/object declarations. Typed
objective conditions now resolve their Story key by condition class and source
field shape, including `CheckRepeatableTalkFinish`. Exact LevelScript property
conditions can attach native Story playback only when level, script, property,
value, property-change event, and downstream typed action all agree; this
recovers the shared `isAllTalkFinished` trigger between `c31m3d5_q#8` and
`radio_c31m3_21` without ordering quest completion against playback. Generic
server-placeholder and LevelScript-condition boundaries close the other source
contexts graph-neutrally when no typed Story consumer exists. The current queue
has zero quests without a strict attachment or bounded diagnostic, with 13
closed diagnostics and no validation failures across main, character, and
other missions. Mission Pipeline shows the exact MissionRuntime, LevelData,
LevelScript, proxy, native event/action, source hashes, and reopening boundary;
unknown/shared directions normalize to visible context instead of disappearing
from the inspector. OCR and manual order were not used as evidence.

The preceding recovery batch closes the six-file character frontier through four
current-build patterns rather than per-object declarations. Authored
`dlg_*` playback is normalized mechanically onto emitted `misc_dlg_*` pages;
the same alias also lets registered DialogTree definitions retain their exact
runtime root. AirWall radio context now validates every typed mission-state
transition predicate (`rise`/`down`, `equal`/`not_equal`) instead of assuming
one hard-coded pair. Text-only cutscenes require an exact localized TextTable
group plus complete absence from Timeline, TextAsset/root, reverse-PPtr,
typed action/playback, carrier, GameAssembly, and metadata surfaces. Finally,
foreign LevelData shells attach exact LevelScript playback and both source
files without transferring Story ownership. This closes
`cutscene_c6m1_1`, `misc_dlg_c6m1_1d5`, `misc_dlg_c6m1_21d5`,
`radio_c6m1_23`, `radio_c31m1_12`, and `radio_c16m2_25`; character
actionable core-isolated rows fall from six to zero. The `sourceStoryGapQueue.v114` offline and
runtime-config validators are active with zero failures. Mission Pipeline
shows the authored alias, transition predicates, foreign mission shell, and
the exact DialogTree, TextTable, LevelScript, LevelData, GameAssembly, and
metadata files. None of these relations creates a relative Story-order edge,
and OCR/manual order remains comparison-only.

The preceding recovery batch generalizes exact black-screen carrier recovery
across three original-data classes: typed DialogTree narrative actions,
serialized Timeline subtitle carriers, and typed native black-screen actions.
It requires complete exact carrier coverage for a Story key and validates each
closure against the current source shape; partial carrier coverage remains
actionable, and validator failures identify the mission, Story key, expected
and actual carrier sets, source paths, and hashes. This closes five character
files (`black_c31m1_3`, `black_c31m2_5`, `black_c33m2_2`,
`black_c17m2_1`, and `black_c13m3_0d5`) plus two newly matching non-character
rows without per-file rules. Character actionable core-isolated rows fall
from 11 to 6 and other rows from 427 to 425; five character quests still lack
a strict Story attachment. Mission Pipeline now preserves unscoped exact
Timeline/DialogTree containment, distinguishes carrier context with unresolved
ownership from unresolved playback, and attaches CAB, playable, track, root,
DialogTree, and LevelScript files. Its recovery cards show exact parent keys
and Timeline ids. Containment, internal tree adjacency, native shell context,
filenames, addresses, OCR, and manual order create no ownership or relative
order edge. The `sourceStoryGapQueue.v113` carrier validator has zero failures,
and the graph remains 1,485 strong edges, 302 native branch groups, and 18
convergences.

The preceding recovery batch generalizes exact local LevelScript playback without
inventing mission ownership. A row qualifies only when every typed playback
occurrence has a current `gameassembly-*` ActionBase mapping, exact Story
identity, an existing hash-recorded source file, and a complete serialized
event path whose terminal action matches the playback record. The decoded
event must explicitly carry neither a mission/quest id nor a server exchange;
mission-bound paths are exclusions, and malformed exact paths fail closed with
structured and CLI diagnostics. This binary-first classifier validates 338
local playback keys across 140 nominal missions with zero failures. The
separate mission-flow gate attaches only the 36 keys across 15 missions that
still have no routed bridge, including six character files across `c6m1`,
`c31m3`, and `c13m2`. Character actionable core-isolated rows fall from 17 to
11 and other rows from 454 to 427. Mission Pipeline attaches source hashes and
the original GameAssembly mapping, while its cards show the exact native
event-to-action chain, related original-data files, and explicit
activation/order boundaries. Trigger slots, local ids,
action-list positions, file order, suffixes, OCR, and manual display order add
no ownership or chronology. The graph remains 1,485 strong edges, 302 native
branch groups, and 18 convergences.

The preceding recovery batch adds a third declaration-free current-build
definition pattern. It requires an exact MemoryPack `DialogId` registration,
an exact decoded `Beyond.Gameplay.DialogTree` with a verified source hash, a
unique mission target, and zero typed LevelScript action/native playback,
object-carrier, mission-route, or installed-binary root-token consumers. An
optional exact `dlgtl_*` definition is attached as internal presentation only:
its line/track structure, source roots, and any internal option graph do not
prove an external activator or cross-file order. Positive playback, runtime,
definition, or non-mission evidence always takes precedence over negative
consumer-surface exhaustion. The classifier qualifies 380 definitions across
113 missions; precedence leaves 59 newly deferred gaps visible (18 character
files across seven missions and 41 other files across 18 missions), including
three with attached dialog-Timeline roots. Validators report zero failures.
Character actionable core-isolated rows fall from 35 to 17 and other rows from
495 to 454. Exact `ReadingPopUpTable`/`RichContentTable` recovery remains at
192 keys across 71 missions, and generic unregistered dialog recovery remains
at 121 keys across 33 missions. All three patterns are definition/consumer
boundaries, not playback, activation, or chronology evidence: table/registry
order, line/option ids, filename suffixes, OCR, and manual order add no graph
edge. The graph remains 1,485 strong edges, 302 native branch groups, and 18
convergences.

The preceding batch generalized SNS and cutscene definitions. The SNS
classifier distinguishes 214 definition-only conversations from seven exact
authored mission links by requiring `relatedMissionId`, a type-12
`linkMissionId`, and `contentParam` to agree. The cutscene classifier requires
bidirectional Timeline registration, decoded TextAsset identity, a typed
`CutsceneRootComponent` hierarchy, and a resolved root `PlayableDirector`, then
applies the same negative consumer boundaries. It qualifies 28 roots across 19
missions without treating an executable definition as an activator.

The preceding `gm02m21` batch recovers its exact native quest topology and closes
its two remaining actionable radios without inventing placement. Hash-locked
MissionRuntime proves the main path `q#1 -> q#2 -> q#3 -> q#4 -> q#5` and the
auxiliary fork `q#1 -> q#6`. The q#6 objective requires q#2 state 3, while its
one-way failure condition refers to q#1 state 3; this does not prove mutual
exclusion or a player-choice branch. The q#2 objective is an exact five-part
AND over LevelScript `map02_lv007/10200190002` stages 1, 2, 3, 4, and 7. That
LevelScript contains five independent typed PlayRadio action roots for
`radio_gm02m21_{1,2,3,5,8}`; their serialized list positions are not execution
order. `radio_gm02m21_4` and `_7` are absent from every typed playback record,
their three authored audio ids are absent from AudioDialog, and complete
AnimeStudio object/reverse-PPtr plus installed-binary token audits find no
consumer. Mission Pipeline attaches the exact MissionRuntime and LevelScript
files, displays the fork, dependency, failure guard, stage conjunction,
present playback roots, and absent targets, and keeps both unresolved radios at
graph effect `none`.

The latest playback-alias audit generalizes the same fail-closed principle to
serialized `CutsceneRoot._director` PPtrs. The current corpus has four exact
root-to-TimelineAsset aliases, but a standalone alias proves playback only.
The gap queue now closes an isolated target only when its current trigger
manifest also contains a mission-consistent, independently connected native
playback route ending at the root Story key, the exact
`CutsceneRoot._director -> TimelineHandle.Play -> target` suffix, complete
native/audit source files, and the expected original-binary mapping. This
qualifies only `cutscene_gm02m4_1`: its root `cutscene_gm02m4_3` is reached by
the exact gm02m4 client-global-variable event and `PlayCutsceneAction` path.
Mission Pipeline shows the composed root, native path, MissionRuntime,
LevelScript, VFS chunk, and reverse-PPtr audit together, with graph effect
`none` and an explicit no-relative-order boundary. The three e11m2/f1m9d4
aliases remain owner-unresolved because their roots have no equivalent owned
route. This changes no graph edge or branch count.

The preceding `gm02m4` audit generalized native branch recovery instead of
adding a mission-specific rule. LevelScript control paths now admit repeated
local-id records only when every typed control field is semantically
equivalent; conflicting duplicates still fail closed. This recovers six
additional exact branch groups across the corpus: the gm02m4 Split and five
sm2l2m2 Switches. gm02m4's exact Split at local id 7 has arm 0
`radio_gm02m4_15 -> _16 -> _17` and arm 1 `cutscene_gm02m4_2`; the radio arm
terminates, while only the cutscene arm continues through local ids 10 and 11,
so there is no authored convergence between the arms. MissionRuntime remains
the linear chain `q#11 -> q#3 -> q#7 -> q#8 -> q#9`. q#3 is an exact AND over
six `InteractiveCheckInt` entity/state comparisons, now exposed generically in
Mission Pipeline with entity ids and comparator targets. Native branch rows
retain the complete MissionRuntime and LevelScript source-file set.
`radio_gm02m4_11` is now closed by the generic current-build classifier: its
exact definition remains visible, but all accepted consumer surfaces are
negative. Both it and the composed cutscene context remain graph-neutral and
are not placed from OCR, manual order, suffixes, audio, or table order.

The preceding `gm02m15` batch closes its two remaining actionable radios without
inventing placement. Hash-locked MissionRuntime is a strict
`q#1 -> q#2 -> ... -> q#8` predecessor chain with no quest fork or merge. Its
q#5 objective is an exact `{0} and {1} and {2}` conjunction over LevelScript
`map02_lv006/25000120003` booleans `jianbei1`, `jianbei2`, and `jianbei3`: all
three predicates are required, but their evaluation order and Story placement
are not serialized. `radio_gm02m15_9` and `_12` occur only as current
RadioTable definitions; all six authored audio ids are absent from AudioDialog,
and no typed MissionRuntime, LevelScript, GameplayConfig, complete AnimeStudio
object carrier, GameObject/reverse-PPtr host, or installed-binary root token
supplies a consumer. Mission Pipeline shows both source-bounded gaps, the exact
linear quest topology, q#5 conjunction, MissionRuntime and LevelScript files,
and graph effect `none`.

The preceding `gm02m8` batch proves that its apparent “nine, six, three items
remaining” dialog progression is not a current runtime branch. Hash-locked
MissionRuntime contains only the linear quest chain `q#1 -> q#2 -> q#3`, with
no client action map or mission properties: `dlg_gm02m8_1` is the exact NPC
mission-accept dialog and q#3 observes `dlg_gm02m8_5` finish 0. The intermediate
`dlg_gm02m8_2`, `_3`, and `_4` roots each survive only as two DialogTextTable
rows. They have no DialogId registration, DialogTree TextAsset, Timeline,
DialogOption rows, AudioDialog membership, typed MissionRuntime/LevelScript
consumer, Lua/object-index carrier, or AnimeStudio carrier candidate; their
exact roots are absent from both current installed binaries. Mission Pipeline
now exposes all three as original-data-bounded activation gaps, attaches their
table and mission-topology files, and keeps graph effect `none`. Their localized
wording is useful cross-reference only and does not prove playback.

The preceding `gm02m17` batch adds one original-binary-backed Story edge and
closes its remaining two actionable files without guessing. Current-build
formatter tag `0x048c/9` identifies `ShowUIReadingPopPanel`; LevelScript
`map02_lv008/23100300006` has an exact custom-event chain from
`StartDialogAction(dlg_gm02m17_11)` to that action, while the mirrored,
fully framed LevelData BriefData property `readingPop` resolves through
`ReadingPopUpTable` to `text_gm02m17_1`. Mission Pipeline therefore shows the
strong edge `dlg_gm02m17_11 -> text_gm02m17_1` and the related LevelScript,
LevelData, and table files. The same MissionRuntime has the exact quest fork
`q#1 -> {q#3,q#4}` and merge `{q#5,q#1} -> q#4`, but only `q#1` is authored
main path and server placeholders hide successor selection; this is not
promoted to a player-choice branch. `radio_gm02m17_2` and `_4` remain exact
one-line RadioTable definitions with missing AudioDialog ids and no recovered
consumer across MissionRuntime, LevelScript, GameplayConfig, object indexes,
or direct native-token surfaces. Their offline closure is visible in Mission
Pipeline with graph effect `none`.

The current main-story isolated-scene queue is source-bounded: all 586 core
isolated rows are now either closed by exact native/runtime/definition evidence
or deferred after current-build offline carrier exhaustion; none remain broadly
actionable. The latest batch closed the last two broad main-story quest
co-memberships as explicitly non-owning diagnostics and exhausted all eight
`a1m5` definition/branch rows. `e10m3d5_q#7` tracks the exact doctor proxy and
its mission-bound `dlg_e10m3_2` row, but its server placeholder exposes no
playback or completion carrier. `e2m8_q#5` reads `CarParked` from exact
`getterList#2`; the three Story calls in that LevelScript are separate action
records. Neither case creates a quest-to-Story or order edge.

`dlg_a1m5_5` is exact authored branch context rather than dead standalone text:
registered `dlg_a1m5_2` contains its two trunks behind a no-bypass seven-way OR
over completed quests `q#4`, `q#5`, `q#8`, `q#10`, `q#12`, `q#14`, and `q#16`.
Mission Pipeline attaches that source file and branch context, while retaining
the boundary that it does not identify one unique trigger or mission-relative
chronology. The seven `text_a1m5_*` files remain exact ReadingPopUp/RichContent
definitions with no recovered activator.

The seven `text_a1m9_*` judge-note files are now closed to the same strict
boundary. Original `ReadingPopUpTable` rows `rp_text_a1m9_1` through
`rp_text_a1m9_7` each target one exact RichContent payload, but exact searches
of MissionRuntime, typed LevelScript/LevelData interactive carriers, and both
current object indexes find no activator. The current structured export has no
Lua corpus, so Lua is a reopen condition rather than claimed negative evidence.
This removes seven rows from the event queue without adding ownership or order
edges.

The next binary-first event batch closes five more actionable rows without
inventing chronology. `radio_a1m6d1_1` plays on the exact local
leader-enter-trigger path in LevelScript `22800970016`; typed MissionRuntime,
NpcProxyEx, and WorldEntityRegistry joins place that authored segment shell in
mission `a1m6d4`, not the nominal `a1m6d1`, and do not select one quest or
relative order. `dlg_a1m6d5_8` is the exact `type_id` of the interactive tracked
by `a1m6d5_q#4`; this proves a client navigation target, not playback.
`text_a1m6d5_1` is an exact ReadingPopUp/RichContent definition without a
recovered activator. `dlg_a1m7_2` and `dlg_a1m7_12` have exact DialogText rows,
no DialogId/DialogTree/Timeline/audio consumer, and no recovered carrier;
`dlg_a1m7_2` has three exact DialogOption definitions, but no original route
graph. Mission Pipeline exposes these files and boundaries.

The remaining nine event rows are now source-bounded too. Exact typed
MissionRuntime tracking attaches `sns_a1m1_1` and `sns_a1m13_1` to `q#1` in
their nominal missions, but `SnsTrackingInfo` is navigation context rather
than playback. The registered `dlg_a1m4_1` DialogTree's exact prime-node paths
reach both `dlg_a1m4_2` trunks; the quest observes only parent-dialog
completion, so activation and inter-file chronology remain unresolved.
`radio_a1m6d1_2`, `radio_a1m6d2_1`, and `radio_a1m6d3_1` are exact one-line
RadioTable definitions whose audio ids are absent from current AudioDialog and
whose audited native/original-data surfaces expose no activator. `dlg_a1m2_4`
is registered and selectable through an empty-mission NpcProxyEx row;
`dlg_a1m11_3` is text/option-definition only. `sns_a1m8d1_1` has a complete
20-node internal content graph and six exact option routes, but no recovered
mission activator. These closures create no guessed ownership or order edge.
Both main-story and event core-isolated queues now have zero actionable rows.

The four-file `a1m8d3` event frontier is closed without using OCR or manual
order as evidence. Original `dlg_a1m8d3_2` DialogTree connections place
`black_a1m8d3_1_001` exactly after `dlg_a1m8d3_2_009` and before `_010`; this
is line-level containment, not a complete file-order edge. Original LevelScript
segment `10100620005` reaches `black_a1m8d3_2` through an exact
leader-enter-trigger to `NarrativeBlackScreenAction` path and is the exact
global segment of tracked proxy `liaowuhen_map02_v1d2d0_005`, proving only
mission-shell playback context. `dlg_a1m8d3_2` and `radio_a1m8d3_1` remain
hash-locked runtime definitions without recovered activators; their current
audio ids are absent from `AudioDialog`. Mission Pipeline exposes all four
boundaries and keeps the mission score at zero.

The 13-file `gm02m2` major-mission frontier is now source-bounded as well.
Exact original tables retain four DialogId-registered roots with 16
DialogText lines and nine DialogOption definitions, plus nine RadioTable roots
with 15 lines. None has current AudioDialog membership. The four dialogs have
no DialogTree TextAsset, Timeline membership, NpcProxyEx consumer, typed
MissionRuntime/LevelScript carrier, exact GameAssembly root token, or typed
object-index carrier; all 13 keys are in the current hash-locked no-candidate
carrier audit. The two multi-choice groups remain visible with their exact
option ids, but their destinations and file chronology are unresolved and no
longer scored as an unsearched runtime-route surface. Because `gm02m2` has no
MissionRuntimeAsset, Mission Pipeline now publishes an explicit zero-node,
zero-edge Story-only recovery shell (also used for `e5m4` and `e5m5`) instead
of hiding the attachments in a global overlay. This lowers major actionable
core-isolated rows from 213 to 200 without creating ownership or order edges.

The 12-file actionable `gm01m22` frontier is now fully source-bounded, reducing
major-mission actionable core-isolated rows to 179. Exact MissionRuntime meta
attaches `dlg_gm01m22_1` to the mission-accept interaction at
`jite_map01_005`; this proves mission ownership and accept-phase placement, not
a relative file edge. The registered parent `dlg_gm01m22_hapo` has exact
prime-reachable typed carriers for `dlg_gm01m22_6` and `_8`, while quest 27
observes completion of the parent; the parent activator remains unknown.
Original DialogTree connections recover `_6` option group 3 as a three-way
split, `_8` group 6 as a two-option convergence on line `_019`, and `_8` group
9 as a three-way split. Seven other dialogs/radios, `sns_gm01m22_2`, and
`text_gm01m22_5` remain exact current-build definitions without a recovered
activator; exact UTF-8/UTF-16 root tokens are absent from the current
GameAssembly. Mission Pipeline displays all eleven definition boundaries,
the internal routes, the accept attachment, and both parent-carrier contexts.

The 10-file `gm02m3` frontier is now source-bounded, reducing major-mission
actionable core-isolated rows from 179 to 169. Original tables retain three
MemoryPack DialogId roots with 19 DialogText rows and seven option definitions,
two unregistered DialogText groups with 11 rows and three more option
definitions, and five one-line RadioTable roots. All 35 dialog/radio audio ids
are absent from current AudioDialog. The six suffix-like DialogId strings
`1X`, `1Y`, `2Y`, `2Z`, `3Z`, and `3d` are printable-root tokens only: their
exact index records are not MemoryPack records and contain no trunks, lines,
options, or Timeline ids, so they are not branch destinations. Exact current
GameAssembly UTF-8/UTF-16 scans find none of the 10 roots or six printable-only
tokens. Direct installed-VFS scans also find no `gm02m3` reference in all 1,291
Lua files or the four patch/extend-data blocks. MissionRuntime, typed
LevelScript/LevelData, DialogTree, Timeline, NpcProxyEx, object-index, source
graph, and carrier-audit surfaces expose no consumer. Mission Pipeline publishes
a fourth Story-only shell with all 10 definitions and three route-unresolved
multi-choice groups; the manual/OCR positions remain comparison-only.

The nine-file `gm01m6` frontier is now source-bounded, reducing major-mission
actionable core-isolated rows from 169 to 160. Five exact `NpcProxyEx` entries
select registered DialogTrees, but every entry has an empty `missionId` and no
serialized selection condition. MissionRuntime quests `q#3` and `q#10` track
`heerman_map01_001`, the same proxy that selects `misc_dlg_gm01m6_3d7`; `q#12`
tracks `heerman_map01_default`, the same proxy that selects `dlg_gm01m6_6`.
These joins prove mission HUD/navigation context only, not dialog playback,
quest ownership, or chronology. The six DialogTrees have no internal multiway
branch group, the three remaining radios are exact definitions without a
consumer, and all nine roots are absent from the current GameAssembly. The
authored quest graph is linear; Mission Pipeline retains only the two existing
`questPrev` Story edges and exposes all definitions, proxy consumers, tracked
quest ids, and exact source files without adding a graph edge.

The nine-file `gm01m7` frontier is now source-bounded, reducing major-mission
actionable core-isolated rows from 160 to 151. Its authored MissionRuntime graph
forks after `q#1` into `q#8` and `q#14`, then joins both at `q#9`; the two arms
and join track the same `sesidun_map01_001` proxy. No serialized client field
assigns a Story file to either arm or exposes the server-side arm-selection
policy, so this is an exact quest fork/join without a Story ownership edge.
Five registered DialogTrees preserve their own exact option behavior:
`dlg_gm01m7_1` has one split and one convergence, while `dlg_gm01m7_3` and
`dlg_gm01m7_5` each have a convergence. Cross-mission `gm01m12` tracking reaches
the proxies that select these dialogs (`q#14` for `dlg_gm01m7_1`, and
`q#2/#3/#4/#6/#12` for the other four) and tracks `sns_gm01m7_1` at `q#16`.
Those joins are navigation context only because the proxy rows serialize no
selection condition and can select multiple dialogs. The remaining radio, SNS,
and reading-popup roots are exact definitions without a playback owner. Mission
Pipeline now exposes the fork/join, dialog-internal branches, cross-mission
tracking, and exact source files while explicitly withholding ownership/order.

The nine-file `gm01m12` frontier is now source-bounded, reducing major-mission
actionable core-isolated rows from 151 to 142. Its exact authored quest graph is
the single chain `q#15 -> q#16 -> q#13 -> q#14 -> q#1 -> q#2 -> q#3 -> q#4 ->
q#12 -> q#5 -> q#6`, with no fork or merge; this is mission context and does
not place any Story file on the chain. Exact LevelScript tasks
`map01_lv001/2100110001` and `2100110003` consume completion of
`dlg_gm01m12_1` and `_3` through `CheckTalkOptionFinish`, respectively. They
prove client-side completion dependencies, not playback, ownership, or order;
the first task also reaches exact post-dialog action
`BlackScreenFadeInAndOut`. DialogTree definitions recover `_1` and `_3` option
convergences; `_6` has no recovered consumer, and unregistered `_8` remains
DialogText/option-definition only. Five reading-popup roots are attached with
their exact table carriers; `text_gm01m12_5` is an authored test-popup stub
without RichContent. Cross-mission `gm01m7` NPC-proxy and archive joins remain
navigation/definition context only. Mission Pipeline exposes all nine files,
their related sources, the linear quest context, and these evidence boundaries.

The `gm01m16` binary-first recovery is now source-bounded: its actionable
core-isolated frontier fell from eight files to zero and its queue score from
40 to zero. Its exact MissionRuntime graph has 26 quests, two entries, five
forks, four merges, eight terminals, and the authored 12-quest
`mainPathQuests` route. Those facts do not
prove branch exclusivity, server successor selection, or Story placement.
`text_gm01m16_4` is now recovered from the exact top-level tail of LevelScript
`map01_lv005/3400160000` as `int_narrative_scene` local interactive `40001`;
the decoder previously mistook the same script id embedded in that interactive
record for the top-level id. Radios `_8`, `_13`, and `_14` are exact RadioTable
definitions whose audio ids are absent from AudioDialog and whose exact roots
have no consumer outside tables across the current installed VFS and
GameAssembly surfaces. Mission Pipeline exposes their hash-locked mission
topology and source file without adding ownership or order. Radios `_1`, `_5`,
`_6`, and `_15` now have exact native playback contexts. `_1` is the radio in
the typed LevelFunctionArea trigger whose `hideAfterMissionId` is `gm01m16`;
the same row independently carries `e2m5` as `hideBeforeMissionId`. `_5` and
`_6` are type-9 radio actions at points 1 and 14 of fully consumed patrol
`160002` in `map01_lv005_lv_data_sub_gm01m16.json`. `_15` is a type-9 action
inside patrol `20001` in `map01_lv005_lv_data_sub_02.json`; its action and
neighboring patrol boundaries are exact, but an unrelated nested event-pair
layout prevents a complete point-index decode, so the point stays unknown.
Current installed metadata maps `PatrolSubActionForMemoryPack.Deserialize` to
token `0x06004bae` / RVA `0x3467210`, and native patrol consumers include
`NewNpcAIPatrolController._PlayRadioSubAction` (`0x0600aed9`). These patrol
records serialize no mission/quest identity, so Mission Pipeline exposes their
source files, patrol/action offsets, and point boundaries without creating an
ownership or relative-order edge.

The `gm01m20` frontier is now source-bounded too: its queue score fell from 40
to zero and all eight actionable isolated files are closed to current-build
evidence boundaries. The exact seven-quest graph is `q#7 -> q#1 -> q#6 -> q#3
-> q#4`, then forks to terminal `q#2` and `q#10`; `mainPathQuests` chooses
`q#2` for its authored display path, but no client field reveals the server's
successor-selection policy. `q#3` observes DialogId root `dlg_gm01m20_8`.
Its decoded 22,173-byte DialogTree payload is byte-identical to
`dlg_gm01m20_2` (SHA-256
`B12B8E56E1A1161DB3D2783680897C0941FBE2845CF3ADB3262320FC28A7F2C0`),
so Mission Pipeline attaches the canonical Story file to both `q#1` and `q#3`
and labels the second route as exact root identity, not activation or branch
selection. `dlg_gm01m20_2` retains its exact two-option internal split. The
four other dialogs are registered DialogTrees selected by empty-mission
`NpcProxyEx` rows; `dlg_gm01m20_1` and `_7` share Kupe's proxy with four exact
quest tracking rows, but that is HUD/navigation context only. Radios `_1`
through `_4` are exact one-line RadioTable definitions with missing
AudioDialog ids and no recovered consumer across the hash-locked carrier and
native surfaces. The WebUI exposes all eight closure cards, the exact alias,
and the unresolved quest fork without adding a guessed file-order edge.

The `gm01m24` frontier is now source-bounded from original serialized data:
its queue score fell from 40 to zero and all eight actionable isolated files
are closed to explicit current-build boundaries. This mission has no
`MissionRuntimeAsset`; the similarly named `m1m24` tutorial asset is a separate
namespace and is not ownership evidence. Exact member-22 LevelData dictionary
`map01_lv006_lv_data_sub_gm01m24` configures `start_dialog = dlg_gm01m24_1`,
`succeed_dialog = dlg_gm01m24_2`, and `failed_dialog = dlg_gm01m24_3` for
LevelScript `3500190001`. Its exact local custom-event path reads integer
property `result` through `SwitchInt`: case 8 reaches `StartDialogAction` via
`succeed_dialog`, while case 9 reaches it via `failed_dialog`. These two paths
are mutually exclusive outcome branches after the configured start dialog;
the client asset does not serialize the custom-event producer or a mission
quest owner. `dlg_gm01m24_1` also retains its exact three-way internal
DialogTree split. Unregistered `dlg_gm01m24_5` is DialogText/option-definition
only, and radios `_1d5`, `_2`, `_3`, and `_4` are one-line RadioTable
definitions with missing AudioDialog ids and no recovered consumer. Mission
Pipeline publishes a fifth zero-node Story-only shell, shows the two exact
result branches and both source files, and keeps OCR/sibling/manual routes as
comparison-only evidence.

The `gm01m25` frontier is now source-bounded under the same evidence policy,
but from its own independently validated carrier. Exact LevelData
`map01_lv007_lv_data_sub_01` binds `start_dialog = dlg_gm01m25_1`,
`succeed_dialog = dlg_gm01m25_2`, and `failed_dialog = dlg_gm01m25_3` to
LevelScript `2800020003`. Local custom event `#33fa174c` reads integer property
`result`: case 8 reaches the success DialogTree and case 9 reaches the failure
DialogTree through unique serialized `StartDialogAction` paths. The two outcome
trees each preserve a second exact choice boundary: option 1 targets a
FinishNode with serialized `finishId = 1`, while option 2 targets a FinishNode
whose `finishId` field is absent; the recovery deliberately does not guess its
runtime default. `dlg_gm01m25_1` retains its authored three-way internal split.
Unregistered `dlg_gm01m25_5` and radios `_1d5`, `_2`, `_3`, and `_4` remain
definition-only with missing current AudioDialog ids and no recovered consumer;
their manual/sibling option layout remains comparison-only. Mission Pipeline
publishes a sixth zero-node Story-only shell with both original source files,
the mutually exclusive result cases, and the exact terminal option routes.
This lowers the mission score from 40 to zero and the major actionable backlog
from 116 to 108 without adding a guessed ownership or chronology edge.

The `gm01m26` frontier is now independently source-bounded. Hash-locked
LevelData `map01_lv005_lv_data_sub_01` binds `start_dialog = dlg_gm01m26_1`,
`succeed_dialog = dlg_gm01m26_2`, and `failed_dialog = dlg_gm01m26_3` to
LevelScript `3400010017`. Local custom event `#3ebdaf39` reads integer property
`result`; exact `SwitchInt` case 8 reaches the success DialogTree and case 9
reaches the failure DialogTree through unique serialized `StartDialogAction`
paths. Both outcome DialogTrees preserve the same second choice boundary:
option 1 targets serialized `finishId = 1`, while option 2 reaches a FinishNode
with no serialized `finishId`. The start DialogTree has an exact three-way
split to lines `_014`, `_017`, and `_009`. Registered repeat dialog
`dlg_gm01m26_5` has a separate exact three-way split to `_014`, `_006`, and
`_008`, but no recovered activator, so it remains definition-only rather than
being placed before or after the race. Radios `_1d5`, `_2`, `_3`, and `_4`
also remain definition-only; `radio_gm01m26_1` retains its separate exact
leader-trigger path. Mission Pipeline publishes a seventh zero-node Story-only
shell with the two original carrier files and all four DialogTree assets. This
lowers the mission score from 40 to zero and the major actionable backlog from
108 to 100 without promoting OCR, overrides, suffixes, or sibling patterns.

The `gm01m5` frontier is now closed as an exact empty-host case rather than a
recovered playback sequence. Mission-named LevelData
`map01_lv001_lv_data_sub_gm01m5` has one validated member-22 BriefData entry,
LevelScript `2100100004`, with no properties, property map, or world-entity
references. The hash-locked LevelScript has serialized action-list count zero,
no decoded UID action/header/getter records, and no task maps. It therefore
cannot activate or order the four nominal dialogs or four radios. The dialogs
survive only as 23 exact DialogTextTable rows and seven DialogOptionTable rows;
none has a DialogId registration, DialogTree, Timeline, or current AudioDialog
membership. The option rows prove authored choices but expose no route graph.
The four radios survive only in RadioTable and likewise have no current audio
membership or recovered consumer. Mission Pipeline attaches both original
empty-host files to all eight definition cards and shows the zero property,
UID-record, action, and task counts. This lowers the mission score from 40 to
zero and the major actionable backlog from 100 to 92 without treating OCR,
overrides, table order, or suffixes as evidence.

The `gm02m1` frontier is now source-bounded as retired definition-only content,
not reconstructed as a playback sequence. An exact-boundary scan of all
179,925 current structured Data/Json objects finds no `gm02m1` carrier, and
there is no exact MissionRuntimeAsset, LevelData, LevelScript, DialogId record,
DialogTree, Timeline, AnimeStudio object carrier, Lua/object-index carrier, or
current AudioDialog membership. The hash-locked installed `GameAssembly.dll`
also contains none of the eight exact Story/root tokens in UTF-8 or UTF-16.
What survives is limited to 13 DialogTextTable rows, four DialogOptionTable
rows, and five RadioTable definitions. Each option group has exactly one
choice; those rows prove authored prompts but neither a branch nor a response
route. `misc_dlg_gm02m1_1d5` is now validated against its distinct original
definition root `dlg_gm02m1_1d5`. Mission Pipeline publishes a ninth
Story-only shell, attaches the exact definition and negative-registry source
files to all eight cards, shows the consumer/order/reopen boundaries, and keeps
all 28 scene pairs unordered. The locked manual order remains display-only
cross-reference, and no OCR or option override exists. This lowers the mission
score from 40 to zero and the major actionable backlog from 92 to 84.

The `gm02m23` frontier is now source-bounded, lowering its score from 35 to
zero and the major actionable backlog from 84 to 73. The hash-locked authored
MissionRuntime graph has 10 quests: its main path is `q#1 -> q#2 -> q#11 ->
q#3 -> q#7 -> q#8 -> q#13 -> q#10 -> q#6`, while `q#2` also reaches `q#9`.
`q#9` carries an exact failed `CheckQuestState` guard against `q#11` state 3;
this proves the client-visible quest fork and guard, not the server's successor
selection policy. Original DialogTree `OpenUI` nodes and exact
`ReadingPopUpTable` joins place `text_gm02m23_1` at the finish of
`dlg_gm02m23_1`, `text_gm02m23_2` between lines `_003` and `_015` of `_3`,
`text_gm02m23_4` at the entry of `_7`, and `text_gm02m23_3` between lines
`_001` and `_002` of external carrier `_9`. The carrier is retained without
inventing a standalone Story parent. Registered `dlg_gm02m23_3` preserves two
two-option convergences and one mixed transition/direct terminal group;
registered `_10` preserves its two terminal routes. `radio_gm02m23_2` remains
an exact one-row RadioTable definition whose audio id is absent from
AudioDialog. Exact scans of 179,925 current Data/Json objects, the typed carrier
audit, and the installed GameAssembly expose no additional consumer for these
three roots. Mission Pipeline shows all five containments, the dialog-internal
branches, the quest fork/failed-state guard, and the definition boundaries.
OCR and manual overrides had no `gm02m23` entries and were not evidence.
The three records formerly reported as missing Timeline activation evidence are
now correctly classified as exact typed DialogTree definitions:
`dlg_gm02m23_1` on `q#1`, `_7` on `q#8`, and `_8` on `q#6`. Together they
contain 33 authored lines, nine option groups, and three multi-option groups.
Their current-game TextAsset hashes are verified again when Mission Pipeline
data is published. `CheckTalkOptionFinish` proves that each quest observes the
dialog's completion state; it does not identify the client action that starts
the dialog. The WebUI therefore shows the definition, internal branch counts,
observer type, source path, and SHA-256 without promoting the internal graph to
a cross-file order edge. The same fail-closed publisher now covers 435 exact
definitions globally, including nested `CheckRepeatableTalkFinish` objectives
and failed-dialog guards, with no silently unplaced definition.

The `gm01m14` frontier is now source-bounded, lowering its score from 35 to
zero and the major actionable backlog from 73 to 66. Its authored
MissionRuntime topology has two forks (`q#1 -> q#4/q#12` and
`q#11 -> q#2/q#3`) and one merge (`q#4/q#12 -> q#5`). Six typed tracking
objectives in that mission and level all name exact proxy
`sesidun04_map01_001`. Hash-verified `NpcProxyExDataTable` rows 2-5 configure
`dlg_gm01m14_2`, `_1`, `_3`, and `_6`; the installed client confirms that the
server's one-based `activeCondIndex` selects the row before the local
interaction reads `dialogId`. The two server pushes carry proxy state but no
mission id, quest id, dialog id, or scene order, so this is shared mission
context only: it does not select one of the six quests and does not order the
four dialogs. Exact LevelScript interactive carriers separately close `_4`,
`_5`, and `text_gm01m14_1`. `dlg_gm01m14_7` and popup definitions `_4`/`_5`
have no current original-data activator and remain offline-exhausted. Mission
Pipeline exposes all seven exact contexts, active proxy row numbers, candidate
quests, server fields, and the order boundary. All 55 scene pairs remain
unordered; OCR, manual order, suffixes, and gameplay observation were not used
as evidence.

The `gm01m27` frontier is now source-bounded as retired/incomplete mission
content, lowering its score from 30 to zero and the major actionable backlog
from 66 to 60. No `MissionRuntimeAsset` survives, so there is no original quest
graph from which to recover a fork, merge, or scene assignment. The three
dialogs survive as 12 exact `DialogTextTable` rows and seven single-option
`DialogOptionTable` rows; all 12 audio ids are absent from `AudioDialog`, and
none has a DialogId registration, DialogTree, Timeline, AnimeStudio carrier,
or typed playback consumer. The three radios likewise survive only as four
`RadioTable` lines whose audio ids are absent. Exact root tokens are absent in
both the hash-locked installed `GameAssembly.dll` and
`global-metadata.dat`. A separate original `PrtsReading` group,
`term_map01_lv001_gm01m27`, has two exact terminal entries with authored orders
1 and 2, inverse numeric-id registrations, and 11 matching mission/objective
`TextTable` keys. Mission Pipeline attaches that related four-table bundle but
keeps its boundary explicit: the terminal order applies only to those two PRTS
entries and supplies no dialog/radio activation, quest join, or cross-file
order. All 15 pairs among the six Story files remain unordered; the manual
display list is cross-reference only.

The `gm02m20` frontier is now source-bounded, lowering its score from 25 to
zero and the major actionable backlog from 60 to 55. Its original
`MissionRuntimeAsset` proves a ten-quest main path (`q#1`, `q#2`, `q#10`,
`q#11`, `q#3`, `q#6`, `q#4`, `q#7`, `q#5`, `q#8`). Auxiliary `q#9` has no
predecessor edge and is not a fork arm: its exact objective is
`CheckQuestState(q#1, state 3)`. The mission has no authored predecessor fork
or merge. A separate exact `map02_lv008/23100270001` LevelScript switch uses
the inline `summon_times` parameter to select radio `_5`/`_16` versus
`_6`/`_15`; this local combat branch does not reference the remaining five
isolated radios. DialogTree evidence recovers two real internal option-route
groups, while ten other option groups converge and are cosmetic. The five
remaining definitions (`radio_gm02m20_7`, `_8`, `_10`, `_11`, and `_13`)
contain seven exact `RadioTable` lines, all with audio ids absent from
`AudioDialog`. They have no match in MissionRuntime, LevelScript, other
structured JSON, AnimeStudio carrier, GameObject, or reverse-PPtr evidence;
their exact roots are also absent from both hash-locked installed binaries.
Mission Pipeline now attaches the exact mission topology and `q#9` state
dependency to each source-bounded card without assigning any of those five
radios to a quest, branch, or relative Story position.

The `gm01m17` frontier is now source-bounded, lowering its score from 20 to
zero and the major actionable backlog from 55 to 51. Its exact 22-quest
`MissionRuntimeAsset` has an authored six-quest main path (`q#1`, `q#2`,
`q#13`, `q#14`, `q#16`, `q#18`), three predecessor forks, no merges, eight
entry quests, and 12 terminals. The `q#2` fork lists `q#13`, `q#22`, and
`q#3`; `q#13` lists `q#14` and `q#15`; `q#4` lists `q#20` and `q#5`.
These successor sets do not themselves prove exclusivity. The one exact
failure guard is directional: `q#13` fails when `q#3` reaches state 3. In the
opposite direction, three nested conditions in `q#3` and one in `q#4` accept
`q#13` state 3 as an alternative objective condition. The validator now
recovers nested `CheckQuestState` paths and fails closed with the exact path.
The remaining radios `_4`, `_5`, and `_9` are one-line `RadioTable`
definitions whose declared audio ids are all absent; `text_gm01m17_1` is an
exact two-content `ReadingPopUpTable`/`RichContentTable` definition. None of
the four has a MissionRuntime action, structured carrier, AnimeStudio carrier,
GameObject/reverse-PPtr candidate, or installed-binary root. Mission Pipeline
attaches the runtime file and displays the main path, forks, directional
failure guard, and nested state dependencies on every source-bounded card,
without assigning a quest or Story order. The manual suffix list is comparison
only, and no OCR proposal exists for this mission.

The `gm01m2` frontier is now source-bounded, lowering its score from 20 to
zero and the major actionable backlog from 51 to 47. No nominal
`MissionRuntimeAsset` exists. Instead, exact binary LevelData
`map01_lv001_lv_data_sub_gm01m2` contains three LevelScript briefs;
`2100210004` has 38 properties and binds `start_dialog`, `succeed_dialog`, and
`failed_dialog` to `dlg_gm01m2_1`, `_2`, and `_3`. Its local custom event
`#72a43b08` reads integer `result`: exact `SwitchInt` case 8 reaches the
success DialogTree and case 9 reaches the failure DialogTree through unique
serialized `StartDialogAction` paths. This proves mutually exclusive outcome
selection within the configured race script, but neither a quest owner nor the
producer of the local event. The exact DialogTrees also recover their internal
branches: `_1` begins `012 -> 013 -> 017`, then offers two menu loops, one
long terminal route, and one short terminal route; `_2` has two terminal
outcomes; `_3` has two terminal outcomes and reuses `_2` option `1_002` for
its absent-`finishId` route. Id-less disconnected `DialogTreeExActorNode`
decoration is now ignored narrowly while every other id-less graph node still
fails closed. `dlg_gm01m2_5` has seven text rows and three option rows but no
DialogId registration, DialogTree, audio membership, or recovered consumer.
The installed binaries contain none of the four dialog root tokens, and the
carrier, GameObject, and reverse-PPtr audits expose no additional consumer.
Mission Pipeline publishes a zero-quest Story shell with the two original
carrier files, exact result control paths, internal option routes, and explicit
missing-`MissionRuntime` boundary. Neither OCR nor the manual order file has a
`gm01m2` entry.

The `gm01m3` frontier is now source-bounded, lowering its score from 20 to
zero and the major actionable backlog from 47 to 43. Its exact authored quest
chain is `q#4 -> q#1 -> q#2 -> q#3 -> q#5 -> q#6`; independent entry `q#8`
also joins at `q#6`. The five strict Story attachments follow that chain, but
the client does not assign the other four files to its branch arms.
`radio_gm01m3_3d2` has an exact local
`EntityEvent_OnInteractiveStateChanged -> PlayRadio` path in LevelScript
`2100010026`. That script is a sibling in the complete 14-entry LevelData
dictionary scoped by typed `gm01m4_q#1` script conditions and entity tracking,
so the WebUI shows a cross-mission `gm01m4` runtime shell without transferring
ownership or chronology. Original `SNSDialogTable` attaches `sns_gm01m3_1`
through both `relatedMissionId` and terminal content node 4; its internal
`1 -> 2 -> 3 -> 4 -> -1` graph orders messages only. Registered two-line
DialogTree `misc_dlg_gm01m3_1d5` and one-line radio
`radio_gm01m3_3d8` remain exact definitions without recovered activators;
all three declared audio ids are absent from current `AudioDialog`. The manual
order conflicts with the authoritative quest chain and has no OCR corroboration;
it remains comparison-only.

The `gm01m13` frontier is now source-bounded, lowering its score from 20 to
zero and the major actionable backlog from 43 to 39. Exact MissionRuntime
predecessors form main path
`q#1 -> q#2 -> q#3 -> q#4 -> q#8 -> q#9 -> q#5 -> q#7 -> q#11`,
plus auxiliary arm `q#2 -> q#12 -> q#4`. The client serializes no branch
exclusivity or server successor selector, so this is a fork/rendezvous topology,
not evidence of a player-choice branch. Registered DialogTrees
`dlg_gm01m13_2` and `_3` are exact NpcProxyEx entries 1 and 2 on
`sesidun02_map01_001`; nine quest objectives track that same proxy for
navigation, but no selection condition assigns either dialog to one quest.
Both trees prove internal group-1 option convergence only, and all ten authored
audio ids are absent from current `AudioDialog`. `dlg_gm01m13_5` retains 15
text rows and four option definitions but has no DialogId registration,
DialogTree, Timeline, audio membership, or original-data consumer; its manual
option routes remain comparison-only. `text_gm01m13_1` is an exact
ReadingPopUp/RichContent definition without an interactive carrier, while
`text_gm01m13_2` and `_3` retain exact LevelScript interactive configuration.
The manual scene list is suffix order and there is no OCR proposal; neither is
chronology evidence. Mission Pipeline now exposes all four source-bounded
activation gaps, the NPC tracking context, internal convergence, and the exact
quest fork/merge while preserving all 36 cross-file pairs as unordered.

The `gm02m14` frontier is now source-bounded, lowering its score from 15 to
zero and the major actionable backlog from 39 to 36. Registered DialogTree
`dlg_gm02m14_1` embeds every `dlg_gm02m14_3` trunk behind exact conditional
node 9. The serialized predicate is `map02_lv005` script `90002` property
`canskip == true`. Current `GameAssembly.dll` proves
`DialogTreeIfNode.GetNextIndex` returns outgoing index 1 exactly when
`GameCondition.result == 1`; authored connection index 1 reaches child node 14,
while index 0 stays in parent lines `_007` through `_009`. The hash-locked
carrier validator therefore adds the strong conditional edge
`dlg_gm02m14_1 -> dlg_gm02m14_3` and reopens it on any source, path, line-set,
or polarity mismatch. Radios `_1` and `_12` remain one-line `RadioTable`
definitions: their audio ids are absent from `AudioDialog`, their exact roots
are absent from both installed binaries, and the current typed/object-index
surfaces expose no consumer. Mission Pipeline shows those two bounded gaps and
the exact linear 12-quest topology without placing either radio on it. Manual
and OCR order remain comparison-only.

Manual order, OCR, filenames, table order, numeric suffixes, and gameplay
observation are comparison evidence only. They never promote an original-data
ownership or chronology edge.

The `gm02m13` frontier is now source-bounded, lowering its score from 15 to
zero and the major actionable backlog from 36 to 33. Its hash-locked
MissionRuntime graph proves main path `q#5 -> q#6 -> q#7 -> q#15`, four
predecessor forks, and the six-arm merge at `q#15`. Three exact authored
failure guards also expose the dialog-completion alternatives on `q#6`, `q#8`,
and `q#9`; they describe quest failure conditions, not radio placement. The
three remaining one-line RadioTable roots (`radio_gm02m13_3`, `_4`, and `_5`)
have audio ids absent from AudioDialog and no consumer in the audited
MissionRuntime, LevelScript, GameplayConfig, object-index, AnimeStudio carrier,
or direct native playback-caller surfaces. Exact roots and audio ids are also
absent from both installed binaries. Mission Pipeline attaches the original
tables and MissionRuntime file, renders the topology and guards, and keeps all
three radios graph-neutral. Filename suffixes, row order, OCR, and manual order
remain cross-reference only.

The `gm01m4` frontier is now source-bounded, lowering its score from 15 to
zero and the major actionable backlog from 33 to 30. Hash-locked
MissionRuntime proves only the linear quest chain `q#1 -> q#2`: q#1 is the
AND gate over exact scripts `2100010048`, `2100010049`, and `2100010050`,
while q#2 watches `dlg_gm01m4_6` and tracks NPC proxy
`luoke_map01_v1d0d0_gm01m4man`. Exact missionless NpcProxyEx entries on that
same proxy select `dlg_gm01m4_3d5` at index 1 and `dlg_gm01m4_7` at index 3;
the indices are server-selected rows, not playback chronology. The former
DialogTree contains the exact group-1 split to lines `_002` and `_004`; the
latter is a linear two-line tree. `radio_gm01m4_1` remains a one-line
RadioTable definition without a typed consumer. All nine authored audio ids
for these three files are absent from AudioDialog, and their exact roots,
audio ids, and proxy id are absent from both installed binaries. The audited
MissionRuntime, LevelScript, GameplayConfig, object-index, AnimeStudio carrier,
and native playback-caller surfaces expose no activation owner. Mission
Pipeline now attaches the exact definitions, proxy rows, q#2 navigation
context, and linear topology while keeping all three files graph-neutral.
Manual and OCR order remain comparison-only.

The `gm01m15` frontier is now source-bounded, lowering its score from 15 to
zero and the major actionable backlog from 30 to 27. Hash-locked
MissionRuntime proves the exact q#3 fork into q#4 and auxiliary q#13 and the
AND rendezvous at q#6, which requires both predecessors; this is parallel
mission work, not a player-choice branch. No quest serializes a Story-file
assignment. Unregistered `dlg_gm01m15_7` has 11 exact DialogText rows, five
exact option definitions whose routes remain unresolved, and an exact
DialogSummary artifact, but no DialogTree, Timeline, audio membership, NPC
proxy, LevelScript, or typed runtime consumer. `text_gm01m15_1` has an exact
ReadingPopUp/RichContent payload plus PRTS archive carrier
`nar_digital_map01_research1_16_1`; its catalog order is not chronology.
`text_gm01m15_8` is an exact ReadingPopUp/RichContent definition without an
activator. Exact roots, option ids, dialog audio ids, archive/proxy ids, and
target text roots are absent from both installed binaries, and the audited
AnimeStudio, object-index, LevelScript/LevelData, MissionRuntime, and gameplay
surfaces expose no additional carrier. Mission Pipeline now shows all three
gaps, their exact related files, and the parallel rendezvous while keeping
them graph-neutral. Manual/OCR sibling-route matches remain cross-reference
only.

Shipped-Lua Story playback is now recovered by one corpus rule rather than a
per-cutscene or per-table list. The complete 1,290-module audit finds ten
bounded `GameAction` playback calls. It admits the exact literal
`cutscene_e1m10_1`, and a general `Tables.<name>` row-field dataflow now also
traces `SkipChapterTable[skip_chapter_1].bindDlgId` through the shipped
`ActivitySkipChapter1ConfirmCtrl` to `GameAction.StartDialog`. That same exact
row co-carries `missionId=e5m1`, so `dlg_e5m0d5_1` gains a mission-level Lua
playback attachment and both the Lua and original table files appear in Mission
Pipeline. One case-mismatched literal remains rejected only after the installed
GameAssembly/metadata audit proves case-sensitive `StringPathHash` resolution.
The other seven calls are not unresolved authored references: one structural
native audit proves they are branches of the same polymorphic cinematic queue.
`CinematicQueueItemDataBase` carries `cinematicId`, the handle carries `id` plus
`data`, and seven typed payload classes expose their identity through getters
selected by `queueItemType`. Current GameAssembly bodies map all seven
dispatchers. The audit now discovers the enqueue sink by its queue-base
parameter, walks callers transitively, and scans the complete action-framework
virtual surface plus same-type helper closure. It finds ten native producers
(eight direct entry points plus two wrappers) and 16 typed serialized action
routes without payload, action, or Story-id allowlists. Mission Pipeline joins
those types only onto already exact LevelScript playback routes, attaching the
original LevelScript and binary-audit files to 1,682 routes across 1,332 Story
files. This annotation adds no ownership or ordering edge: mission/quest scope
still comes only from the serialized action row and its authored event/control
path. Multi-row table fields stay candidates unless their lookup key is proven.
Lua without a same-row mission/quest foreign key proves controller playback
only, never Story order; OCR and manual order do not participate.

## Remaining gaps

1. **Mission ownership:** 156 Story files have exact native playback but lack a
   mission/quest activation bridge. The unresolved surface is organized under
   161 runtime receiver nodes and 186 receiver-to-Story placements. Twenty-seven
   of those Story keys now have exact Encounter-controller and related-file
   context, but remain unowned. The general activation-frontier publisher now
   attaches 237 placements of 141 distinct authoritative LevelScript,
   LevelData, MissionRuntime, SpawnerConfig, gameplay-config, and table files
   found recursively in the typed evidence; these are related context, not
   inferred owners. `cutscene_e1m10_1` likewise has an exact
   shipped-Lua phase owner but no serialized mission/quest identity.
2. **Black screens:** 65 remain unassigned. Most are definition-only or lack a
   current-build playback consumer; five have playback but no static owner.
3. **Story recovery queues:** all quest-attachment gaps are now either strict
   typed attachments or bounded graph-neutral diagnostics. Main, event, major,
   character, and other missions have no actionable core-isolated files. The
   remaining 17 missing MissionRuntime bundles stay explicit Story-only shells;
   broad co-memberships remain non-owning diagnostics.
4. **Option routes:** no multi-choice group remains broadly actionable after
   exact current-build carrier exhaustion; unresolved groups remain visible and
   reopen only when a typed DialogTree/Timeline/runtime consumer appears.
5. **Narrative video:** three placement groups remain unresolved:
   `cs_video_e1m3_3`, `remotecomm_e1m2_2`, and `remotecomm_e1m2_3`.
6. **Total ordering:** most scene pairs are unknowable from current static
   evidence. A display order must remain separate from source proof.

The highest-value missing source is a serialized server/runtime registry that
contains both LevelScript and mission/quest identity. Next inspect other
repeated typed LevelData property contracts and their native controller
consumers, but publish them first as related system/file context. Repeating
existing LevelScript, DialogTree, Timeline, teleport, proxy, Encounter, or
local carrier scans is unlikely to close ownership without a new foreign key
or changed inputs.

The repeated module-property census is now bounded: seven full Encounter
families use the existing typed controller contract, while eight
`map02_lv006` families expose only base `LevelScriptModule.is_enabled` and
`is_completed` state. The installed `LevelScriptModule` layout/consumers show
that the two-field shape is generic lifecycle plumbing and carries no
mission/quest identity, so it must not be promoted to an owner type. The next
ownership pass should require a new co-carried foreign key in another typed
controller payload or native registry, not a module id, LevelSequence name,
file address, or registration order.

The eight unmatched BlackBox rows are now source-bounded current-build
definitions, not open placement candidates. Reopen them only if a changed
binary or serialized producer/consumer surface contains an exact row identity;
numeric suffixes, dungeon sort ids, guide-hint names, task ids, asset paths,
OCR, and manual order remain non-evidence. Highest-value next work is the 156
exact native playback files that still lack a mission/quest activation bridge,
especially repeated typed LevelData receiver contracts that may expose a new
foreign key. The former final three isolated keys are now closed by general
provenance rules: every exact `SNSDialogTable` identity, regardless of filename
prefix, passes the same authored graph, route, typed playback, complete
AnimeStudio carrier, and installed-binary token gates; this admits
`test_sns_emojicomment` and `test_sns_sticker` as shipped definitions with no
current consumer while retaining their internal SNS branches/options. Generated
Story entries may be excluded only when index and conversation payloads carry
matching `project_authored` provenance and the declared repository producer
exists; this excludes `black_webui_secret_notice` without treating it as game
evidence. Mission Pipeline publishes all three as graph-neutral Story-only
shells with related table/carrier/binary or project-source files. Schema v130
has zero validator failures and zero actionable core-isolated scenes.
Within `gm02m23`, the
remaining source-bounded activation gaps are `dlg_gm02m23_3`, `_10`, and
`radio_gm02m23_2`; the former Timeline records `_1`, `_7`, and `_8` are closed
as quest-observed definitions. The seven isolated and four weak-only Story
files have zero broadly actionable rows under the current audited sources. For
`gm01m16`, reopen the
patrol rows only if an exact `NpcPatrolStart`, world-entity, or MissionRuntime
tracking join co-carries patrol `160002` or `20001`; do not infer that join from
the mission-like filename or patrol registration order. Reopen a
deferred row only when a new typed producer/consumer or changed source hash
supplies an ownership or order edge.

## Evidence rules

Accepted chronology requires a typed authored relation such as quest
predecessors, exact DialogTree continuation, decoded option routes, exact
LevelScript playback control paths, or proven spawner progression.

Keep as non-ordering context:

- source co-membership;
- native registration;
- mission-state dependencies;
- preload/remove/override actions;
- definition-only media;
- receiver or level scope without a mission bridge.

Reject as proof:

- filename and suffix order;
- file/list/code-address order;
- OCR or manual order;
- spatial proximity;
- observed gameplay without an original-data carrier.

## Maintained reports

```text
reports/story/build/mission_pipeline_story_binding_coverage_CN.md
reports/mission_order/source_story_partial_order_CN.md
reports/mission_order/source_story_gap_queue_CN.md
reports/story/recovery/native_receiver_activation_frontier.md
reports/story/build/narrative_videos_CN.md
```

Useful commands:

```bat
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
python tools\endfield_source_graph.py story STORY_KEY
python scripts\story_recovery\build_source_story_gap_queue.py --language CN
```

Treat report counts as current truth; this note records only the stable
interpretation and highest-value gaps.
