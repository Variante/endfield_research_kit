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
- Every one of the 152 exact-native-playback ownership gaps now has an
  active-overlay, source-hash-gated trigger classification. The current corpus
  resolves 66 to one exact authored local trigger volume, 2 to multiple exact
  authored volumes, and 84 to exact non-spatial local event carriers, with no
  unresolved spatial selector. This identifies the per-file local trigger
  carrier only; it does not prove mission ownership, event firing, branch
  choice, activation, or Story order.
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
- Keep parser and validator failures deterministic, bounded, and actionable.
