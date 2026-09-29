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

## Deferred bounded Story capture plan

Planned, not implemented, and authorizing no capture until explicitly
revisited. Operational commands and capture restrictions are owned by
[`EndfieldCapture/README.md`](../../tools/EndfieldCapture/README.md); the
generic gameplay-semantics profile is not a Mission/LevelScript/Story tracer,
so recheck provider capabilities when resuming.

The maintained mission trace has dialog acceptance and playback-key hooks,
but its manifest targets an earlier client and its read-only current-install
preflight refuses the executable identity. The supported `EndfieldCapture`
profiles still have no Story-key, chosen-option, initiating-action and accepted
playback identity in one observation or validated correlation chain. Audio
posts and optional recording can show a voice request in a bounded session,
but cannot promote that request to a selected dialog option or Story trigger.
Revalidate a narrowly selected current-build Story method and its source
carrier before authoring a dedicated capture profile or requesting a session.

- Start from one concrete static-evidence gap and one short, repeatable NPC
  interaction leading to one Story and its completion callback. Record the
  initial mission/objective, interaction target, and chosen option. Existing
  bounded audio capture plus optional recording can establish observed
  playback, never its trigger or mission ownership.
- Before a dedicated observer, authenticate the current native inputs and
  validate each selected method body, ABI, payload boundary, and identity
  carrier. Observe only
  `trigger -> condition result -> LevelScript action -> Story start/end -> callback or quest-state change`,
  retaining source-connectable trigger/entity/LevelScript identities,
  condition inputs and results, Story key and initiating action,
  playback-instance lifetime, callback/successor identity, and supplied
  mission/quest identities where proven.
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
  `reports/story/recovery/`, and durable conclusions here. Expand to quest
  conditions and cross-Story callbacks only after the first chain has a
  complete identity join.

## Remaining gaps

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
