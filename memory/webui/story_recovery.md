# Game Story recovery

Cross-page Story reconstruction model, indexed from
[`README.md`](README.md) beside the page guides that consume it. Story page
behavior itself is [`story.md`](story.md). The carrier-level LevelScript,
Timeline, native-gate, and spatial-placement rules live in
[`../game_data/story_carriers.md`](../game_data/story_carriers.md), because they
describe how the installed bytes are read rather than how Story is presented.

This topic owns the evidence model used to reconstruct Story structure,
ownership, branches, activation carriers, and partial order. It is a separate
file because the same recovered evidence feeds Story, Map, Audio, source-graph
queries, standalone Mission Pipeline investigation, and validation reports;
the Story page consumes those results but does not define their truth
conditions.

## Current status

The maintained builders recover dialog, radio, SNS, cutscenes, options, inline
media, localized references, mission grouping, and an evidence-typed partial
order. The result supports research but does not claim a complete canonical
playthrough. Current coverage and gap counts live in `reports/story/`.

## Evidence model

Evidence is layered and never silently upgraded:

1. authored Story structure: DialogIdTable, DialogTree, Timeline, conversation
   tables, option definitions, and narrative media;
2. mission structure: quests, predecessors, objectives, failures, typed actions,
   and source files;
3. runtime configuration: LevelScript, LevelData, SubGame, spawners, interactive
   records, and shipped Lua;
4. installed-binary contracts: exact-build IL2CPP/native behavior;
5. cross-reference only: OCR, manual order, filenames, proximity, and gameplay
   observation.

Only validated typed relations from the first four layers may create accepted
ownership, connection, placement, or order edges. Layer five guides
investigation and presentation only.

Name matching defaults to case-insensitive comparison while preserving authored
spelling. A folded match is accepted only when unique; collisions fail closed.

## Maintained code boundary

Production parsers, validators, joins, attachment logic, and generated schemas
live in `scripts/webui/story/`. Audits, candidate enumeration, OCR, native
probes, and report-only CLIs live in `scripts/webui/story_recovery/`.

The dependency is one-way: recovery tools may import stable builder primitives;
production builders must not import or execute recovery modules. Promote a
recovery algorithm by moving its pure, tested core into `scripts/webui/story/`
and leaving only report/CLI orchestration in `story_recovery`.

The protocol registry publishes only after every required validator and the
after-read selected-native gate pass. Refusals write a bounded `.failed.json`
companion and leave the published JSON and Markdown untouched. An absent
optional native event route retains its explicit ownership/transport gap.
Reuse also binds the complete raw reader/contract snapshot and the registry
script. Fresh and reused reports recheck both that recipe and the selected
native pair before publication; unchanged game files do not excuse code drift.

The language builder and its DialogTree connection projections use native
citations and NPC consumers from one authenticated evaluation per language.
The builder authenticates again before successful
completion and refuses changed native inputs, claims, or complete raw-reader
inputs. This keeps row generation consistent without a process-wide validation
cache or repeated binary hashing for every row.

The source-only partial-order report likewise owns one native evaluation for
one build operation. Its nested projections share that proof; standalone
helpers validate independently. Before returning a report, it rechecks its own
source, selected native pair and complete raw-reader inputs. Drift aborts with
a bounded structured diagnostic. No proof survives into another operation,
and failed or pending native groups still contribute no native conclusion.
The source Story gap queue also passes that explicit report-owned scope to
proxy selectors and token/address citations. Revalidating the complete reader
dependency graph for each row makes a full queue needlessly slow. Its final
source/native/reader checks finish before the queue is published; standalone
helpers retain their own validation, and no proof survives the report.

## Story structure and media

- DialogTree and Timeline recover local line order and explicit option routes.
  A local branch does not imply a cross-Story continuation.
- Unscoped narrative-carrier rows may aggregate several parent dialogs.
  Validate each explicit action's parent, require complete declared-parent
  coverage and retain every typed source/path check. This closes carrier
  context only; parent ownership, activation and file order stay unresolved.
- A shared-only option response remains an explicit frontend continuation even
  when no option has exclusive lines. An ancestor branch may already remove
  that response from the outer trunk; discarding its local shared lines then
  hides both the dialogue and the next anchored prompt. The nested choices in
  `dlg_sm2l10m1_17` exercise this case.
- A repeated-question menu with exactly one advancing choice presents that
  choice's response below the menu. The choice itself stays beside the looping
  questions. Admit this layout only when every other option explicitly returns
  to the same menu and all outcomes of the advancing option reach a later
  prompt in the same scene; unknown or multiple exits retain branch columns.
- DialogTree and Timeline source hashes read the authoritative Unity store.
  When a disposable filtered Timeline extract is absent, attachment and director
  recovery use the original stored objects. Root selection must remain unique;
  component joins require the exact serialized source file and PathID. A missing
  store row or an object from another source file remains unresolved even when a
  loose copy or the same PathID exists elsewhere. An empty parent-dialog set
  produces a validated empty index; a missing index still fails validation.
- Multi-output control nodes preserve every decoded arm and polarity. A shipped
  producer does not prove which arm executed.
- Cutscene is a presentation union. Rooted Timeline, component-only Timeline,
  LevelScript FMV, mixed carriers, and text-only candidates remain separate.
- Operator-spacecraft Story classification is rebuilt from source-hash-checked
  tables and authored DialogTrees in the selected export. It is not pinned to
  a historical installed-binary version and carries no native addresses.
- Factory guide-radio classification likewise uses the selected export's
  complete AnimeStudio object index, source fingerprint, exact managed type,
  and same-action serialized fields, without a historical native hash gate.
- Subtitle attachment requires an authored link or one unique complete ordered
  match across the selected language/gender tracks. Partial and ambiguous
  matches fail closed.
- **Some authored Subtitle Track ids have no localized text row, but their
  Timeline clips may still carry literal display text.** Every
  `SubtitlePlayableAsset._textId` absent from `TextTable` is also absent from
  all exported Table and Json payloads (including packed `Json/LipSync`) and
  from every decoded `TextAsset.m_Script`. It is not an extraction gap: a
  current Table VFS index (Persistent over StreamingAssets) matches the
  exported Table name set, a targeted active `TextTable` dump is
  byte-identical to the export, and the focused and full structured scopes
  both export every Table and JsonData block. A source-CAB-local `m_Asset`
  PPtr joins every absent-key asset to a serialized Subtitle Track clip; many
  such clips have literal, language-specific `m_DisplayName` strings, others
  store `<key not found>` or an i18n error string. `m_DisplayName` is an
  authored clip display field; its text does not prove the runtime subtitle
  getter uses it as a fallback. `DialogCenterTextPlayableAsset` and
  `LeftSubtitlePlayableAsset` resolve completely, so the gap is specific to
  the Subtitle Track family. Per-build counts, keys, and clip inventory are
  generated under `reports/story/recovery/`.
- Video, image, SNS, audio definition, authored placement, activation, and
  observed playback are distinct claims.
- Character Wiki voice rows do not replace responsive or exploration catalogs;
  presentation duplicates may fold while authored trigger records remain.

## Mission and quest ownership

- MissionRuntime predecessors, typed Story actions, objectives, and failures
  form the source-only mission graph.
- Quest forks describe authored topology, not the server-selected arm.
- Client handlers applying supplied mission/quest ids do not prove the client
  selected the successor.
- Exact objective/success relations can order bounded events inside a quest but
  do not prove execution or choose a later fork.
- Definition-only start actions remain definitions until a validated producer
  reaches them.
- Server placeholders and exact playback without a mission/quest carrier retain
  explicit ownership gaps.

## Ordering

The source-only graph is intentionally sparse. Accepted edges preserve evidence
type, direction, source hash, and validation status. It must remain acyclic;
incomparable files remain incomparable.

Hash-shaped CallServer labels that equal the owning action UID are retained as
non-ordering callback diagnostics. Their classification follows the selected
build's reviewed action route, rather than a literal opcode from an older
build. Removing such a label from unresolved Story nodes does not close the
server handoff or add a timeline edge.

DialogTree OpenUI controls retain every serialized outgoing arm. Named native
ports, the native configured default index, and explicit shipped Lua result
producers label those alternatives without choosing one. A UI closing without
an explicit override can resume a configured nonzero outgoing ordinal; assuming
that every default is the first arm loses the current native continuation
policy. Missing producers remain a bounded shipped-corpus finding. The binary,
Lua, and source-identity gates must all pass before publishing those labels.

A Branch iterator's non-Story arms remain part of its action sequence. When
only one arm reaches Story playback, its stored sequence adds useful local
action context but cannot order two Story scenes. Scene-pair incomparability
must therefore be examined by causal carrier, rather than treated as a request
to sort every scene into a total timeline.

Manual inputs are presentation, not source evidence:

- `webui/overrides/story_order.json` is user-managed and never regenerated.
- `webui/data/story_order_ocr.json` contains proposals only.
- `webui/overrides/options.json` retains visible manual tagging.

## Validation policy

Batch Story/Mission recovery edits. During a batch, use focused tests and direct
parser/builder probes. Run the canonical Story/Mission sequence after at least
three independent changes or at the coherent batch boundary, unless a
cross-cutting schema change cannot be validated locally.

Every validator fails closed and reports its name, failed gate, affected
mission/Story key, source path, bounded expected/actual values, and source
hashes in both structured output and the CLI summary. Improve generic
`validation_failed` diagnostics before another expensive rebuild.

## Maintained commands

```bat
python -m scripts.game_data.extraction.verify_export_freshness
python -m scripts.webui.story.refresh_evidence
python -m scripts.webui.story.source_links
python -m scripts.webui.story.build --languages CN --default-language CN
python -m scripts.webui.mission_pipeline.build_mission_pipeline_data --refresh-source-story-gap-queue
python -m scripts.webui.map.build_map_recovery_data --with-preview
```

Reference reuse is allowed only when exported Timeline and Table inputs are
unchanged. Never use it after an installed-game refresh. Allow a long timeout
for Story builds.

Generated outputs live under `reports/story/build/`, `reports/story/recovery/`,
`reports/mission_order/`, `reports/assets/map_recovery/`, and
`reports/source_graph/`. Counts, edge inventories, native addresses, hashes,
per-level examples, and session proof belong there rather than here.

## Saved Story capture evidence

The retained Mission trace format has a dedicated offline preparation and
inspection path. Live observer implementation and launch instructions are
internal-only; see the repository boundary in `AGENTS.md`.
`scripts/game_data/mission_trace_capture_prepare.py` resolves the symbolic
method signatures and typed field paths in the reviewed
`scripts/game_data/contracts/mission_trace_capture.json` against the explicitly
selected client. Preparation authenticates the executable, native image and
metadata, proves field paths and entry ABI, rejects folded method aliases,
and derives fresh body windows. The older retained mission-trace manifest is
an offline reference and does not authorize attachment to a different build.

The provider journals bounded method-entry observations of SNS reading and
resolved option selection, mission and quest transitions, LevelScript source
identities, authored action keys and nodes, dialogue/trunk/option boundaries,
and cutscene, radio and communication requests. Stored strings require a
proved reference read; inline value types retain their stored bits. Optional
null carriers remain visible separately from unreadable or truncated reads.
No getter, dictionary enumeration or engine callback is invoked.

The general profile also observes shared synchronization, objective copy/refresh,
quest-action dispatch, dialogue history/request/condition and LevelScript
task/completion boundaries. Before-copy fields do not prove applied state, and
per-changed-objective tracking carries an objective kind rather than a unique
condition key. Incoming container contents, unchanged items and server rules
remain unresolved. Generic condition polling is excluded from the default
profile because entry frequency is not bounded by state changes.

The mission-specific `OnSubConditionProgressChanged` observer retains the
supplied quest, condition and integer progress alongside explicitly named
pre-entry caches. Its request argument is not a snapshot of every incoming
objective value, and entering the method does not prove delivery or server
acceptance. Clean retained evidence now admits this observer during login
restoration, including explicit quest arguments with null stored owners and
supplied progress differing from the cache. An active identification sequence
now starts `m1m70_q#2` with `isNewQuest=true`, supplies progress `1` with entry
cache `0`, and later retains a `True` result/progress `1` alongside explicit
quest and mission completion. The quest argument, stored parent and archived
objective membership agree. Restoration and this active call share an
authenticated Boolean delegate specialization that widens a condition result
to the integer argument. This closes the active Boolean callback question;
active multi-step numeric updates, live subtype/IFix selection and the earlier
full call stack remain coverage gaps. Advanced-progress UI refresh is a
separate path.

The shared recipe now includes snapshot-group registration/notification,
snapshot-condition lifecycle/callback context, interactive state request and
integer property callback, and incoming interactive-property packet identity.
Preparation has passed against the selected installed client; these additions
have no admitted live-session evidence yet. The snapshot callback now retains
its supplied string group ID alongside stored condition/quest identities,
after separately proving the closed single-reference value layout and its
indirect native argument passing during preparation. Layout alone previously
selected an incorrect inline read and failed in a live photo callback. The
preserved failed journal retains the named group notification, condition
context and a subsequent supplied progress value, but is diagnostic-only;
it cannot supply an admitted payload join or complete mission outcome.
This is an explicit entry association; bound-group matching, callback result
and progression still require additional evidence. Interactive supplied old/new
values and stored pointer/server identities remain separate from applied writes and mission
progress. The bounded source archive includes Snapshot and KiteStation tables
to retain the entrust-to-mission and group-to-target configuration; source bytes
still do not authenticate current-native semantics. See the optional internal
checkout's README for the collection procedure.

The launcher checks the independent recorder during startup, the observed
health baseline and active capture. Unless screen backup was explicitly
disabled, its premature exit, nonzero final exit or absent/incomplete typed
completion receipt prevents the overall saved result. Preserve such sessions
as provisional evidence; a readable earlier journal does not close the lost
screen interval. The string argument proof also rejects unmodeled jumps and
terminators rather than treating them as sequential execution.

A subsequent clean `m1m43` gathering session preserves partial HUD progress,
incoming target identities, the combined-root completion flag, quest handoff
and mission completion. Its archived definition reuses the `m1m41` display
keys while naming a different target set; keep variants distinct by their
explicit mission and objective carriers. The source/packet identity match is
useful evidence, but delivered property and objective numeric values remain
unread. The selected interactive callbacks and snapshot callbacks are unhit,
so this session neither admits an applied property write nor validates the
repaired photo argument in a live invocation. See the combined-objective
boundary in `memory/game_data/story_carriers.md`; generated session details
belong under `reports/runtime_capture/`.

Offline native evaluation now identifies a retained interactive-data consumer
with server-data and loaded-entity property blackboard paths. This provides a
specific alternative to the local root-component callback when investigating
incoming property delivery; it does not identify the path actually taken by
the earlier gathering session. The shared recipe adds receiver/packet identity
at `InteractiveInfo.UpdateServerProperty` and supplied signed old/new state
with explicit entity identity at `NavObstacleManager.OnInteractiveStateUpdate`.
The later clean marker/photo interval retains both entries, with packet and
stored entity identities agreeing within the property consumer and authored
script ownership retained for marker-related entities. Navigation supplies its
old/new states with explicit entity identity. Navigation dispatch is
conditional, and its entry does not prove an applied property write or a
Mission counter update. Delivered
map members, concrete variable values and the incoming objective dictionary
remain unread. Native claims and their limits belong to
`memory/game_data/story_carriers.md`; no Story ordering or generated page-data
change follows from this offline consumer analysis.

The capture objective is a general model of mission behavior across the corpus.
Assess coverage by shared mechanism: restoration versus new acceptance,
partial and combined-condition progress, authored action dispatch, branching,
quest success/failure/pause, and final mission completion. Keep authored
configuration, validated native consumer behavior, observed entries and a clean
end-to-end session distinct. A hook firing once admits that observed case;
installing every hook does not establish coverage of every mission or condition
family. Prefer the next available mission that exercises an uncovered mechanism
over repeating an already understood sequence. Preserve normal login, separate
countable actions with visible progress, and retain the final transition and
any separately performed claim.

The maintained `mission_mechanism_audit` combines a selected exported mission
set, an authenticated shared-native evaluation and admitted timeline receipts.
It keeps stored family coverage, inheritance-based default selector
applicability, quest-entry associations and uniquely owned condition entries
separate. The nearest unreviewed getter prevents an inherited classification;
a quest beside a family does not prove that leaf ran. Its generated census and
offline review priorities belong under `reports/runtime_capture/`. Durable
selector, dependency-graph and typed current-pair rules belong to
`memory/game_data/story_carriers.md`; this audit publishes no Story order or
page data and requires no canonical rebuild.

Selector coverage now admits individually checked named overrides through the
selected objective census, with default enum returns after the IFix guard's
false path. Keep excluded local leaf lanes
separate from combined traversal and from unreviewed families. The complete
normal objective-copy caller has checked values/detail/nested-hash loops, but
copied completion/count data still cannot substitute for a quest-state
transition. The audit now joins selected enum names and reviewed state/AST
consumer claims to those operands, and uses a separately authenticated ASCII
native parser model. AND and OR reduce at equal precedence from left to right;
the audit retains all supplied decision-wait children separately from expression
inputs. Required-true, required-false and alternative roles remain conditional
on live Param initialization, helper/context behavior and coherent nested caches;
each objective is considered separately. References to other
quests or missions do not move the owning objective or add a chronology edge.
The native outer combined evaluator waits for every child to become decided
before evaluating its short-circuit AST. Activation can match existing state,
and a missing current quest record can inherit `Completed` from its completed
owning mission. Reviewed source-zero Param resolvers copy constants before
getter/blackboard dispatch, while typed producer/subscriber contexts and compiled
packet lanes explain local state-event delivery. A changed active result is
cached before its callback and subsequent parent evaluation; callback reentrancy
keeps nested coherence unresolved. These rules explain restored eligibility,
local publication and delayed handoffs; they do not observe a new completion
event or fill a recording gap. Detailed proofs and their limits remain in
`memory/game_data/story_carriers.md`, the shared-native claims contract and
`mission_expression_native.json`. No chronological edge is promoted by this
review, and no canonical rebuild is needed for its report-only audit.

The retained `a1m15` sequence now reaches its final quest success, an explicit
`CompleteMission` entry with a supplied succeed ID, and a `Processing` to
`Completed` state-change entry in a clean package. Its later
`hidden74_a1m15` availability and start have separate notifications. This
closes the observed completion endpoint for that route. The retained activity
configuration independently links the follow-up stage to a mission-state
predicate for `a1m15` and a stored time gate. This proves a configured dependency,
while actual server predicate evaluation, selected time range/timezone, unlock
instant and reward credit remain unresolved. Sequence-level detail, configured
dates and source identities stay in generated capture reports; no automatic
Story ordering override follows.

The default source snapshot covers all available mission definitions and
LevelData/LevelScript/template/configuration families with shared semantic
tables, the binary `DialogIdTable`, and `TimeRangeTable`. The identity table
supports direct stored wire-ID/name joins; the time table preserves configured
ranges without asserting which one the server selected. Older captures may
lack these sources, so separately retained fresh export bytes must be labelled
as current supporting evidence. A focused archive changes only source retention,
not runtime filtering.
The offline inspector uses the retained profile, preserves raw scalar bits/nulls,
and reports observed/unobserved coverage separately from receipt completeness.
Explicit quest membership can join a retained mission definition; pointer reuse,
temporal proximity and concurrent observations do not establish ownership.

`mission_capture_timeline` now makes these distinctions reproducible from a
passing retained inspection. It keeps per-entry identities and fields, marks
restoration separately from new quest entries, and reports configured
predecessors beside the same-thread success/start entries that corroborate
them. The explicit stored main-path list retains nonnumeric quest order as
authored structure, while gaps in observed transitions stay gaps. Missing and
ambiguous mission associations stay visible, including
playback and condition-only objective copies. An optional current-source join
checks observed mission definitions against selected native inputs and current
exported bytes; missing or changed inputs withhold current reuse while leaving
the historical observation labelled as such. These offline reports publish no
Story ordering edges or page data. In the retained completion route, new quest
entries and final mission completion precede the related dialogue exit
callbacks, so exit callbacks cannot substitute for quest progression.

Installation readiness is separate from observed health. The launcher waits
for advancing atomic status snapshots, recorded rows and a sustained healthy
baseline before authorizing progression, and surfaces live losses or failed
reads immediately. A healthy startup baseline does not validate carriers that
have not yet been entered. Hook transitions check thread/context operations,
patches, rollback and resumption; a failed suspension/context/patch transaction
remains failed even if recovery restores execution. An observed pre-suspension
`OpenThread` invalid-parameter refusal had no native changes and clean handle
release. A thread disappearing after the snapshot is a possible explanation,
not an established cause. Only that fully cleaned preparation refusal may
restart the entire strict transaction, for at most three total attempts with a short pause;
it cannot skip threads or retry a cleanup failure. Summary v2 retains every
enable attempt, and live readiness, collection and offline inspection validate
the history alongside the successful final transition. Older v1 receipts have
no attempt history. A retained active gameplay run enables on the first
attempt and collects cleanly; it admits that ordinary path on the repaired
runtime without exercising the preparation-retry branch. Unrecoverable
rollback or resumption retains the
runtime until external process exit rather than running unsafe cleanup.
The assembly observer anchors its stack with a saved frame pointer and restores
flags before a valid Windows epilogue; offline tests check the actual Windows
unwinder at every instruction boundary. A callback timeout retains borrowed
storage and explicitly marks counters provisional. Collection requires stable
final counters with no active callbacks or undrained records.
Journal serialization must succeed before appending or counting a row. A
serialization failure immediately revokes health, preserves earlier valid
records, and accounts for unwritten admitted records; it cannot wait for the
collector to discover malformed JSON after irreversible progression.
A status-publication failure still rejects collection when all admitted rows
were flushed without loss. An independently completed screen recording may
cover later gameplay, but cannot restore missing native entries or turn the
retained journal prefix into a complete capture.
Snapshot readers share deletion and close their handles before parsing or
console output. Existing status documents use `ReplaceFileW`; initial
publication uses a non-replacing move. A bounded open-reader probe demonstrated
that the former replacing-move path could fail despite delete sharing. Failed
publication retains its first file, stage and Windows error, and the host
preserves the provider's original diagnostic. Older receipts without those
details cannot establish the historical failing OS operation.
A clean retail restoration capture with the repaired runtime admits this
publication path through final collection. This complements the bounded
open-reader tests; it does not certify every contention pattern or reclassify
an older failed journal as complete.
The startup/SNS pilot admitted live content updates and the following quest
handoff. That admission covers the observed boundaries; later dialogue and
mission routes still need their own capture evidence. Startup also enters
`StartMission` with `stateChanged=false` and `StartQuest` with
`isNewQuest=false`; later progression enters `StartQuest` with
`isNewQuest=true`. A method entry alone therefore cannot identify a newly
accepted mission or a newly reached quest.

Typed metadata interpretation identifies the observed quest handoff's client
success and client start action phases. These lifecycle dispatches do not prove
that an authored action exists or executed: the retained mission has empty
client action maps. Its explicit predecessor dependency agrees with the
observed handoff, supporting that visited edge without recovering the policy
for all branches. Objective tracking and completion conditions remain separate:
an SNS tracking target can coexist with a server-placeholder condition, and
the client observations do not reveal the authoritative completion rule.
LevelScript runtime state also requires typed interpretation; activation is
not automatically a script-finished event or a Story ordering edge.

The dialogue continuation admitted option selection, ordered trunk entries,
finish boundaries and further quest handoffs. Selected option ids can join
directly to stored `DialogTreeOptionNode` entries read through
`UnityObjectStore` and the maintained dialogue-tree readers, even when the
sampled option carrier's dialogue and trunk fields are null. Keep source
membership separate from the missing runtime carrier fields. Stored tree
connections can independently confirm an observed nonnumeric trunk order;
sorting trunk suffixes would discard that route evidence. A configured
dialogue UI action's dungeon id can also match an observed script level id,
providing a named content association without proving quest selection policy,
action execution or asynchronous causality. Fresh supporting Unity/config
sources outside a session's archive need their own identities and provenance.
Quest success/start entries can precede dialogue-exit callbacks, so exit
callback timing is not interchangeable with dialogue finish or quest handoff.

Decode scalar sentinels
using the retained field type and bit width: a terminal SNS content value can
appear as an unsigned bit pattern for a negative signed integer. Null action
owner keys remain an ownership gap even when capture is lossless.

Join sources through explicit script ids, stored source-path hash bits,
authored action keys and node identities, and observed Story/SNS ids. A clock
or address ordering never establishes source ownership or mission order.
QPC, tick time and a UTC anchor permit comparison with the separate primary
display recording; its first-frame receipt time is an approximate anchor.
Capture context remains unfiltered so intervening events are retained.

Entries establish that a named boundary was entered, not its return value,
successful playback, asynchronous parentage or an initial mission-state
snapshot. Same-thread entry order is observable; concurrent thread timing
does not prove causality. Unchosen routes and activity before capture remain
unresolved. A complete receipt means the observer stopped cleanly with no
recorded losses or failed/truncated reads, not that every mission mechanism
was observed. Preserve partial journals on failure; never publish them as
complete evidence.

- Cross-thread or asynchronous links need validated correlation identities;
  timestamps and process-local pointers do not establish causality or source
  identity. A received server notification does not reveal the server's
  selection policy.
- Hooks stay observation-only and bounded, preserve original calls and results,
  and follow the prelaunch, one-attachment, exact-build, clean-stop, and
  collector gates. Missing hooks, unreadable or truncated payloads, lost
  events, ambiguous joins, or incomplete cleanup fail closed; a key press or
  successful preflight is not evidence that capture completed. Add focused
  positive and negative tests before retail observation.
- Join accepted runtime records back to authenticated static sources before
  publishing edges. One session proves only its observed route. Use separate
  bounded sessions for a repeat and a controlled alternative, never modifying
  game state through the observer. Keep raw sessions in
  `scratch/reverse_engineering/endfield_capture/`, compact reviewed results in
  `reports/story/recovery/`, and durable conclusions here. Additional quest
  condition and cross-Story callback observations need a named missing identity
  join or shared rule that retained sessions and offline consumers cannot decide.

## Remaining gaps

- Mission work starts with retained-session/source reconciliation through
  `mission_trace_inspect` and the shared native claims. Keep authored topology,
  observed quest handoffs, restoration, and unresolved ownership separate;
  collection completeness and hook coverage answer different questions.
- The native expression/parameter review now distinguishes ordinary value
  construction, full MemoryPack field loading and the mission loader's JSON
  paths. Keep exported constants conditional until a capture joins the live
  Param and effective source selector to its condition owner. Native activation
  control paths verify quest subscription before its initial result and mission
  subscription after its initial result. Both can match without a new event;
  neither supplies a completion timestamp. Use the
  [Mission timeline capture requirement](../runtime_capture_requirements.md#mission-timeline)
  to target a continuous handoff and, separately, a state-predicate/combined
  evaluation interval with invocation and outcome linkage.
- The reviewed default Mission client selector and result binder admit only
  `ClientOnly` leaves. Talk-finish and script-property conditions have other
  virtual types, which explains how their specialized hooks can be absent
  while quests progress. Effective scope, live receiver type and IFix selection
  remain separate gaps; the stored `$type` does not establish execution.
- Recover change-level objective and LevelScript property connections through
  authenticated scalar consumers carrying quest/condition or script/property
  identities. Root completion flags and tracking objective kinds cannot explain
  individual combined-condition progress. The retained active identification
  callback answers the Boolean-result question. In `m1m12_q#2`, incomplete then
  complete root flags and screen-visible partial HUD counts accompany explicit
  quest/mission completion, but no per-condition Mission progress callback is
  retained. Individual marker writes and incoming numeric count delivery remain
  unresolved. The observed LevelScript task lane names a different script from
  the archived marker operands and cannot supply their ownership. Script-property
  conditions produce boolean local results, while the reviewed Mission binder
  selects `ClientOnly` leaves. Offline native recovery now establishes the
  stored-value consumer, numeric presentation getters and incoming script
  property-map writer path. A multiple combined objective counts children
  whose stored-progress comparisons pass; its target is the child count,
  independent of the cached condition result. Complete LevelData owners supply
  marker defaults and the brief-data ID-to-key map used by that writer.
  Actual delivered map entries, successful writes and the selected live display
  branch remain unobserved. A new observer must prove field reads, ownership
  and event-rate bounds while preserving the no-getter/no-container-traversal
  boundary. Another capture is unnecessary for the already observed
  identification callback or these recovered default consumers.
  A clean retained `m1m15` marker run now observes the packet and runtime
  property-sync entries naming its authored script, alongside explicit quest
  refresh, predecessor success/new-start and completion entries. The selected
  local Boolean-condition lifecycle/check/event hooks remain unhit. This
  records the named delivery lane for that variant without reading its supplied
  maps, child values or applied writes. The screen independently retains
  partial counts, and root-copy entries remain condition candidates with no
  live quest assignment. Repeating this completed task is unnecessary for that
  identity question. Its displayed name and radio names reuse `m1m9`, so the
  captured quest/script IDs must select the actual definition and graph.
  The same clean run admits the repaired photo group payload at explicitly
  owned condition entries for several active photo quests. Only the
  stored-group matches (`m1m32`, then `m1m31`) have retained progress-one and
  completion entries. A reused condition ID or `GetResult` entry alone cannot
  select the completed quest, and the stored-constant match does not observe
  the live bound parameter or returned comparison result. These observations
  answer the payload/owner association question without another recording;
  dynamic entity-to-marker mapping and numeric/objective-map contents remain
  separate recovery gaps.
- Extend clean completion coverage to other available routes and uncovered
  mechanisms, retaining the supplied completion identity. Select daily variants
  by explicit runtime carriers. Require a complete final receipt; startup
  restoration or a later screen-only completion cannot close a missing native
  transition.
- Revisit exact playback ownership only when server policy, payload-aware
  runtime evidence, or a new typed client carrier becomes available.
- Close more CallServer callbacks and server placeholders through bounded typed
  successors without relaxing the unique-path gate.
- Expand exact LevelScript/Timeline action schemas and callback ownership.
- Improve cutscene activation, subtitles, option branches, and audio lanes.
- Determine why the Subtitle Track ids lack Table rows and whether the runtime
  getter uses any alternate carrier. Distinguish literal serialized
  `m_DisplayName` text from a localized Table row and from observed playback;
  sentinel display fields still have no recovered line text. A future-build
  audit must repeat the active-overlay Table and asset checks.
- Recover stronger cross-file order while preserving partial-order semantics.
- Reduce unlinked Story through typed routes, never filenames, proximity, or
  native address order.
- Keep every parser and validator failure deterministic and actionable.

## Project-authored open-source notice

`black_webui_secret_notice` is emitted for every supported Story data language.
`scripts/webui/story/language_bundle.py` keeps the translations inside its
existing notice emitter and uses the same localized title and text for the conversation, index
preview, and search. Preserve its stable key, line IDs, and
`gameDataEvidence: false` provenance. It is project content and establishes no
game recovery claim.
