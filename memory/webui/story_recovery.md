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

## Story structure and media

- DialogTree and Timeline recover local line order and explicit option routes.
  A local branch does not imply a cross-Story continuation.
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

## Bounded Story capture

EndfieldCapture has a dedicated Mission trace provider. Operational commands
and prelaunch restrictions are owned by
[`EndfieldCapture/README.md`](../../tools/EndfieldCapture/README.md).
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
acceptance. Keep its caller path and live coverage unresolved until observed;
advanced-progress UI refresh is a separate path.

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

The default source snapshot covers all available mission definitions and
LevelData/LevelScript/template/configuration families with shared semantic
tables. A focused archive changes only source retention, not runtime filtering.
The offline inspector uses the retained profile, preserves raw scalar bits/nulls,
and reports observed/unobserved coverage separately from receipt completeness.
Explicit quest membership can join a retained mission definition; pointer reuse,
temporal proximity and concurrent observations do not establish ownership.

Installation readiness is separate from observed health. The launcher waits
for advancing atomic status snapshots, recorded rows and a sustained healthy
baseline before authorizing progression, and surfaces live losses or failed
reads immediately. A healthy startup baseline does not validate carriers that
have not yet been entered. Hook transitions check thread/context operations,
patches, rollback and resumption; a failed transaction remains failed even if
recovery restores execution. Unrecoverable rollback or resumption retains the
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
- Prioritize condition creation and scope/implementation selection: explain why
  a configured `CheckTalkOptionFinish` objective can complete without entering
  its specialized hooks. Trace graph/client/server scope, virtual dispatch and
  IFix routing offline before choosing new observations. The stored `$type`
  does not establish the instantiated receiver or executed implementation.
- Recover change-level objective and LevelScript property connections through
  authenticated scalar consumers carrying quest/condition or script/property
  identities. Root completion flags and tracking objective kinds cannot explain
  individual combined-condition progress. Prove field reads and event-rate bounds
  before adding observers; preserve the no-getter/no-container-traversal boundary.
- Once installation and collection failures are resolved, capture an available
  unfinished route through its final quest and mission-completion entry, retaining
  the supplied completion identity. Select daily variants by explicit runtime
  carriers. Require a complete final receipt; startup restoration or a later
  screen-only completion cannot close a missing native transition.
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
