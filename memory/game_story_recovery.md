# Game Story recovery

## Current status

The Story builder reconstructs dialog, radio, SNS, cutscenes, options, inline
media, localized references, mission grouping, and an evidence-typed partial
order. It is useful for research but does not claim a complete canonical
playthrough.

The current CN corpus contains 5,660 unique Story files. Maintained reports
show 4,304 connected and 1,356 unlinked files. The latest Mission Pipeline
coverage report has 152 unlinked files with exact native playback but no
mission or quest activation bridge. Counts change with rebuilds, so reports are
the source of truth.

## Evidence model

Evidence is layered and never silently upgraded:

1. authored Story structure: DialogIdTable, DialogTree, Timeline, conversation
   tables, option definitions, and narrative media;
2. mission structure: quests, predecessors, objectives, failures, typed actions,
   and source files;
3. runtime configuration: LevelScript, LevelData, SubGame, spawners,
   interactive records, and shipped Lua;
4. installed-binary contracts: fingerprint-locked IL2CPP/native behavior;
5. cross-reference only: OCR, manual order, filenames, proximity, and gameplay
   observation.

Only validated typed relations from the first four layers can create accepted
connection or order edges. Cross-reference evidence guides investigation but
does not prove ownership, activation, or chronology.

Recovery name matching defaults to case-insensitive comparison. Reports retain
the authored spelling, canonical spelling, and ambiguity set; a folded match is
accepted only when it is unique. Case-colliding candidates fail closed rather
than selecting one by file order.

## Maintained code boundary

Production parsers, validators, joins, attachment logic, and generated schemas
live in `scripts/story_builder/`. Audits, candidate enumeration, OCR, native
probes, and report-only CLIs live in `scripts/story_recovery/`.

The dependency is one-way: recovery tools may import stable builder primitives;
production builders must not import or execute recovery modules. When an audit
becomes a production dependency, move its pure core into `story_builder` and
leave only the report/CLI surface in recovery.

## Stable conclusions

### Story structure and media

- DialogTree and Timeline recover most local line order and explicit option
  routes. A local branch does not imply a cross-Story continuation.
- Multi-output control ports preserve every decoded arm and polarity. Shipped
  producer presence does not prove a live choice; absence does not prove
  permanent unreachability.
- Cutscene is a presentation union. Rooted Timeline, component-only Timeline,
  LevelScript FMV, mixed carriers, and text-only candidates remain separate
  semantic shapes.
- Subtitle text attaches only through an authored link or one unique complete
  ordered match across selected language/gender tracks. Ambiguous or partial
  matches fail closed.
- Video, image, SNS, and audio definitions remain separate from playback and
  mission ownership.
- Character Wiki voice rows do not replace responsive/exploration catalogs;
  duplicate presentation may fold while authored trigger records remain.

### Mission and quest ownership

- MissionRuntime predecessors, typed Story actions, objectives, and failures
  form the source-only mission graph.
- Quest forks describe authored topology, not which arm a server selected.
- Client handlers apply supplied mission/quest identities and state; current
  evidence does not expose a general client-side successor selector.
- Exact success or objective relations can order bounded events inside a quest,
  but do not prove that the quest executed or select a later fork.
- Definition-only start actions remain definitions where no validated producer
  exists.
- Server placeholders and unlinked playback keep explicit ownership gaps.

### LevelScript, Timeline, and native evidence

- Serialized action maps, UIDs, action lists, callbacks, and target carriers are
  accepted only through versioned parsers and bounded validation.
- CallServer callback recovery preserves exact typed reverse paths from a
  preceding Story action and exact forward paths from the callback header. A
  strong cross-Story edge requires one complete linear source path, one target,
  and no branch, loop, merge, truncation, or graph-shape mismatch. The current
  corpus has one accepted preceding path but no two-ended Story callback
  closure, so this evidence currently adds no order edge.
- Active LevelScript evidence uses one logical-path overlay: StreamingAssets is
  the fallback and Persistent replaces the complete file. Same-hash shadow
  evidence may normalize to the active path; changed shadow evidence must be
  decoded again from the active bytes or is rejected. Every order-bearing
  LevelScript edge passes this source/hash gate before publication.
- Native facts are locked to exact `GameAssembly.dll` and metadata hashes.
  Missing or mismatched inputs skip that evidence instead of reusing stale
  addresses.
- Registration order and code addresses never imply Story order.
- Timeline track/clip ownership proves authored scheduling, not Director
  activation or Wwise playback.
- Weak LevelScript placement is diagnostic and cannot enter accepted chronology
  unless a typed route closes the gap.
- Active-overlay direct playback enumeration now classifies Story trigger
  carriers independently of the older missionless-receiver subset. Exact map
  placement requires the same typed header-to-playback action path, current
  script and source hash, one exact slot selector, and one decoded authored
  Leader shape. Multiple exact observations remain multiple locations;
  missing slots, ambiguous shapes, preload/load/stop rows, and sibling actions
  remain diagnostic only. A second exact spatial carrier is a current-build
  event payload that selects one constant EntityPtr: specified-entity property
  events and bounded single-entity lifecycle filters may attach the Story to
  that exact WorldEntityRegistry marker. Arbitrary-entity events, dynamic
  filters/lists/paths, and event payloads without an entity selector remain
  non-spatial. A getter-backed validation predicate makes execution
  conditional but does not erase an independently constant specified-entity
  target; publication still records activation, ownership, and order as
  unproven. A subtype may remain opaque while its inherited EntityEvent
  specified-entity scope is decoded independently; that narrow schema proves
  only the constant target and validation fields, never the subtype payload or
  broader event semantics. Multiple typed control paths from the same event header may
  converge on one Story-bearing playback node without becoming sibling
  inheritance; multiple playback nodes or foreign headers remain ambiguous.
  A typed `SpecificEntityListDie` constant list is also spatial evidence for
  each exact list member; it remains distinct from a same-record 3D playback
  target, so one Story may legitimately have multiple authored points.
  `EnemyInFight` uses the same rule when its formatter yields a complete
  constant entity list; dynamic validation affects execution only, and a
  final-header exact subtype prefix remains bounded by consumed members.
  `EntityHpChanged` likewise keeps a fully validated constant entity/ratio
  payload spatial when only its inherited validation predicate is getter-backed.
  Leader trigger-volume list listeners are decoded as bounded constant slot
  lists. Every positive unique slot must resolve to its own typed Leader
  volume and shape; the Story is then published at each explicit authored
  location without choosing, averaging, or collapsing the list. Duplicate or
  missing slots remain fail-closed.
  Patrol-checkpoint listeners attach playback to one unique, fully decoded
  LevelData `NpcPatrolData` point when their patrol id and zero-based point
  index are constant. `ProxyPatrolCheckpointReach` additionally walks its
  nullable outputs and constant proxy-id filter. The non-proxy variant may
  retain a runtime-bound NPC property while its checkpoint tuple is still
  exact. In both cases the point is authored geometry, not the event's runtime
  NPC position, permanent ownership of the patrol, mission ownership, or quest
  activation. A proxy registry/table join corroborates identity but never
  replaces the checkpoint coordinate. When patrol id or point index is a
  mutable named blackboard value, the decoder preserves that exact dynamic
  filter and its event outputs but publishes no checkpoint; an initializer is
  only a candidate until later lifecycle writes are excluded.
  Exact SpawnerPtr filters are spatial only when the same level contains one
  matching `sc_<level>_<id>` SpawnerConfig and one logical typed LevelData host
  record whose finite position/rotation agrees across the active overlay.
  Group filters may be nullable wildcards and output parameters may be present;
  neither changes a separately constant SpawnerPtr filter. Getter-backed
  spawner filters, group/wave text, and event outputs never substitute for the
  spawner identity. Partial known fields are reported separately from a fully
  consumed native subtype. A build-locked `SpawnerPtrGetter` may fold a getter
  reference only when its corrected `payloadStart - 4` member boundary contains
  one complete constant `Param<SpawnerPtr>`; source-200 property getters retain
  their authored initial value as non-final diagnostics and do not place Story.
  Entity-spawn/lifecycle listeners walk the formatter fields in order and
  preserve nullable group/wave filters.  When the listener is the final
  header-list record, the exact consumed subtype prefix is authoritative even
  though the generic byte window also contains following ActionMap lists;
  those trailing bytes are never scanned for a SpawnerPtr.
  A getter-backed inherited validation predicate makes playback conditional
  but does not erase an independently constant, fully decoded SpawnerPtr.
  Start, pause, group-complete, and wave-complete listeners likewise require
  their complete ordered filter/output layout; nullable outputs are consumed
  explicitly, while getter-backed SpawnerPtr values remain non-spatial.
  Wave/group configuration, spawned-entity output, or a raw numeric hit alone
  remains non-spatial.
  Encounter activation and battle-part listeners may resolve to an authored
  spawner host only through a complete constant `LsmPtr` filter, one matching
  typed encounter property family, a positive type-50 `spawner_id`, and unique
  same-level SpawnerConfig and LevelData transform. This locates the authored
  encounter-associated spawner; it does not prove the encounter center,
  runtime enemy position, activation, mission ownership, or Story order.
  NPC interaction dialogs have a separate direct spatial carrier:
  `NpcProxyExDataTable` stores `proxyId`, `dialogId`, and optional mission
  context in one authored selection row, and the build-locked native consumer
  uses the server-selected active row for that same proxy. A dialog may attach
  to the proxy marker only when its case-insensitive published key is unique,
  the proxy id has exactly one self-consistent `npcProxyBriefInfos` identity,
  and NpcProxyTable supplies the same finite position plus finite rotation.
  This proves the dialog is configured for that authored NPC location; it does
  not prove which row the server currently selects, interaction activation,
  quest ownership, or cross-row Story order.
  Generated frontier and map reports own the changing counts.
- For e0m0, the current two-map union has 23 mapped Story keys and 25 disjoint
  unmapped keys. The unmapped set is 15 ordering-graph-only, 8 without spatial
  placement evidence, and 2 mission-scope-only; 17 have exact non-spatial
  event context and 8 have no frontier row. `cutscene_e0m0_1` is the reviewed
  exception recovered under the repository's unique case-insensitive name
  policy: Leader slot 80001 -> stage case 0 -> StartGenderSelect -> phase Lua
  playback, with its authored Box geometry and conditional status preserved.
  No exact spatial frontier
  observation remains unprojected. Source-graph mission/order edges do not
  upgrade these rows to map locations.
- Current offline client-static ownership recovery is exhausted at the known
  native receiver frontier: reverse PPtr, GameObject/carrier, LevelData,
  SubGame, MissionRuntime operand, IFix, and recursive protobuf scans produce no
  exact mission/quest owner for the 152 exact-playback gaps. The current patch
  replaces no receiver-ownership or task-completion target, and no protobuf
  type co-carries mission/quest identity with LevelScript or Story identity.
  Reducing this gap now requires server-side policy, payload-aware runtime
  evidence, or a future client/patch with a new typed carrier.

### Ordering

The source-only graph is intentionally sparse. Accepted edges preserve their
evidence type, direction, and source. It must remain acyclic; incomparable files
remain incomparable.

Manual order is a presentation override, not source evidence:

- `webui/overrides/story_order.json` is user-managed and never regenerated.
- `webui/data/story_order_ocr.json` contains proposals only.
- `webui/overrides/options.json` stores manual option recovery and must retain
  visible manual tagging.

## Validation policy

Batch recovery edits. During a batch, use unit tests, direct probes, or
`--mission-pipeline-data-only` while Story/evidence inputs are current. Run the
canonical Mission Pipeline rebuild after at least three independent changes or
at the end of a coherent 30–60 minute batch.

Every validator must fail closed and report the validator, gate, affected
mission or Story key, source path, bounded expected/actual values, and source
hashes in both structured data and the CLI summary. Improve generic diagnostics
before rerunning the expensive pipeline.

## Maintained commands

```bat
python scripts\verify_export_freshness.py
python scripts\story_builder\refresh_evidence.py
python scripts\story_builder\source_links.py
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\build_mission_pipeline_data.py
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
```

Do not use reference reuse after an installed-game refresh or together with
`--from-game`. Allow at least 15 minutes for direct Story builds.

## Maintained reports

Key generated sources of truth include:

```text
reports/story/build/mission_pipeline_story_binding_coverage_CN.md
reports/mission_order/source_story_partial_order_CN.md
reports/story/recovery/
reports/story/build/
```

Changing inventories, exhaustive edge lists, native addresses, hashes, and
per-run proof belong in reports rather than this file.

## Highest-value remaining gaps

- Revisit exact native playback ownership only when server-side policy,
  payload-aware runtime evidence, or a new typed client carrier becomes
  available; current client-static joins have zero promotable candidates.
- Close the remaining CallServer callbacks across typed event/task successors;
  do not relax the current unique linear-path gate.
- Recover more typed server-placeholder producers and bounded successor logic.
- Expand exact LevelScript/Timeline action schemas and callback ownership.
- Improve cutscene root activation, subtitle, and audio-lane evidence.
- Recover stronger cross-file order while preserving partial-order semantics.
- Reduce unlinked Story files with typed routes, not filename or address order.
- For e0m0, pursue files with no frontier row and new typed spatial carriers;
  revisit an event only when its own payload supplies a build-validated
  constant EntityPtr or authored trigger geometry, never through sibling
  actions or listener proximity.
- Keep parser and validator failures deterministic, bounded, and actionable.
