# Game Story recovery

This topic owns the evidence model used to reconstruct Story structure,
ownership, branches, activation carriers, and partial order. The Story WebUI
page consumes those results but does not define their truth conditions.

## Why this file remains

Story page behavior is documented in [`webui/story.md`](webui/story.md). This
file remains necessary because the same recovered Story evidence also feeds Map,
Audio, source-graph queries, standalone Mission Pipeline investigation, and
validation reports.

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
live in `scripts/story_builder/`. Audits, candidate enumeration, OCR, native
probes, and report-only CLIs live in `scripts/story_recovery/`.

The dependency is one-way: recovery tools may import stable builder primitives;
production builders must not import or execute recovery modules. Promote a
recovery algorithm by moving its pure, tested core into `story_builder` and
leaving only report/CLI orchestration in `story_recovery`.

## Story structure and media

- DialogTree and Timeline recover local line order and explicit option routes.
  A local branch does not imply a cross-Story continuation.
- Multi-output control nodes preserve every decoded arm and polarity. A shipped
  producer does not prove which arm executed.
- Cutscene is a presentation union. Rooted Timeline, component-only Timeline,
  LevelScript FMV, mixed carriers, and text-only candidates remain separate.
- Subtitle attachment requires an authored link or one unique complete ordered
  match across the selected language/gender tracks. Partial and ambiguous
  matches fail closed.
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

## LevelScript, Timeline, and native evidence

- LevelScript actions, headers, UIDs, callbacks, lists, and target carriers are
  accepted only through versioned parsers and bounded validation.
- Active evidence uses one logical-path overlay. Persistent replaces the
  complete StreamingAssets file; changed shadow data is decoded from active
  bytes or rejected.
- A direct playback carrier requires one typed header-to-action path. Preload,
  load, stop, sibling actions, foreign headers, unresolved graph shapes, and
  raw numeric hits remain diagnostics.
- CallServer ordering requires one complete linear Story-to-callback-to-Story
  closure with no branch, merge, loop, truncation, or ambiguous target. A
  one-sided path adds no cross-Story edge.
- Timeline track/clip ownership proves authored scheduling, not Director
  activation, selected option, or Wwise playback.
- Native evidence is locked to exact `GameAssembly.dll` and metadata hashes.
  Registration order and code addresses never imply Story order.

## Spatial carriers

Story may be placed on Map only through the exact carrier's own authored
geometry or identity. Maintained carrier families include validated trigger
volumes, constant EntityPtr targets, explicit entity lists, patrol checkpoints,
SpawnerPtr/encounter hosts, NPC proxy dialogs and envTalk, atmospheric NPC
clusters, narrative components, reading points, and exact 3D radio actions.

Each family has its own schema and uniqueness gate. These rules are shared:

- every constant or getter field is decoded in formatter order and bounded by
  exact consumption;
- dynamic blackboard values, runtime lists, nullable outputs, validation
  predicates, sibling actions, mission context, and proximity never substitute
  for the carrier identity;
- one Story may have several exact authored points; do not choose, average, or
  collapse them;
- placement does not prove activation, mission ownership, runtime actor
  position, or chronology;
- changing per-level carrier coverage belongs in generated frontier and map
  reports.

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
python scripts\verify_export_freshness.py
python -m scripts.story_builder.refresh_evidence
python -m scripts.story_builder.source_links
python -m scripts.story_builder.build --languages CN --default-language CN
python -m scripts.build_mission_pipeline_data --refresh-source-story-gap-queue
python -m scripts.build_map_recovery_data --with-preview
```

Reference reuse is allowed only when exported Timeline and Table inputs are
unchanged. Never use it after an installed-game refresh. Allow a long timeout
for Story builds.

## Maintained reports

```text
reports/story/build/
reports/story/recovery/
reports/mission_order/
reports/assets/map_recovery/
reports/source_graph/
```

Counts, edge inventories, native addresses, hashes, per-level examples, and
session proof belong in those outputs rather than this file.

## Remaining gaps

- Revisit exact playback ownership only when server policy, payload-aware
  runtime evidence, or a new typed client carrier becomes available.
- Close more CallServer callbacks and server placeholders through bounded typed
  successors without relaxing the unique-path gate.
- Expand exact LevelScript/Timeline action schemas and callback ownership.
- Improve cutscene activation, subtitles, option branches, and audio lanes.
- Recover stronger cross-file order while preserving partial-order semantics.
- Reduce unlinked Story through typed routes, never filenames, proximity, or
  native address order.
- Keep every parser and validator failure deterministic and actionable.
