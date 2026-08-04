# Scripts

Maintained scripts support the static WebUI, installed-data export, update
tracking, Story recovery, source graph, and Unity character lab. Prefer the
root wrappers for normal use.

## Root workflows

| Task | Command |
| --- | --- |
| First setup | `.\setup_first_time.bat` |
| Rebuild from current `export_full/` | `.\export.bat` |
| Refresh from installed game | `.\export.bat --export-from-game` |
| Refresh Story and assets | `.\export.bat --export-from-game --with-assets` |
| Story/Mission iteration | `.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference` |
| Mission data only | `.\export.bat --mission-pipeline-data-only` |
| Asset/audio maintenance | `.\export_assets.bat` |
| Build Updates feed | `.\build_updates.bat` |
| Apply installed-game patch | `.\build_updates_by_patch.bat` |
| Serve WebUI | `python serve.py` |
| Package WebUI | `python scripts\pack_webui.py` |

Root wrappers load defaults from `endfield_paths.bat`. Explicit path flags
override those defaults for one run.

## Export rules

- `export.bat` reuses and freshness-checks `export_full/` by default.
- Use `--export-from-game` only for an intentional installed-game refresh.
- Add `--with-assets` when asset indexes and CN audio must refresh too.
- Use `--full-source-graph` only for exhaustive Unity-object/PathID work.
- Use `--mission-pipeline-data-only` only when generated Story evidence is
  already current.
- Canonical `export.bat` runs refresh and validate the source Story gap queue
  after current partial-order and coverage reports are published, before
  Mission Pipeline recovery cards are projected. Data-only runs reuse it.
- Mission Pipeline builds also ensure the protocol registry audit matches the
  exact installed `GameAssembly.dll` and metadata hashes. Its state-update
  census discovers message shapes, typed handlers, runtime field offsets, and
  lifecycle argument flow generically. Its quest-start audit extends the same
  decoder with typed call-return provenance, structurally discovers
  `QuestInfo`, and compares native field reads with metadata topology fields;
  stale, invalid, or missing reports are rebuilt. The whole-client topology
  census re-decodes direct-call candidates inside metadata method bounds and
  uses general register plus entry-relative stack-slot provenance to classify
  every predecessor, flow-index, and main-path consumer. It fails closed on
  an active predecessor reader, a non-sort flow consumer, or any
  topology-driven lifecycle call.
- The same corpus-wide census recovers `QuestType` and `QuestShowMode` enum
  values and follows both `QuestInfo` fields through every verified direct
  getter caller. Its field-driven branch analyzer validates the sole
  `Optional` comparison as an `ObjectiveShowData.optional` write and both
  post-lifecycle `Block` comparisons as `EventManager.SendGlobal` notification
  corridors. It fails closed if visibility reaches lifecycle code, a quest-type
  read interleaves with state application, or a bounded native back-edge could
  revisit lifecycle calls. None of these paths selects a successor arm.
- The protocol audit also recovers the `QuestAction` enum and validates every
  current AOT fallback dispatcher and pending replay into `RunQuestAction`.
  `FailQuest` and `SucceedQuest` are the complete direct `SafeRunQuestAction`
  caller set; the shared pending list is the only replay carrier. The complete
  bounded census currently finds no `OnStartClientAction` producer, so authored
  start rows are published as definition evidence and never order edges. The
  partial-order builder may then join only same-quest objective Story
  completion and native-typed succeed Story actions. This is a corpus rule,
  not a mission/Story allowlist; reverse strong conflicts fail closed, and
  success occurrence or successor selection is not inferred.
- The protocol audit structurally discovers the ActionBase extra-thread list
  and scheduler, then scans every direct child `Execute` body for typed child
  fields or typed collection members flowing into that scheduler/list. New
  writer shapes fail closed. Mission Pipeline uses the admitted current-build
  class names to label parallel `actions[i]` edges; array position never becomes
  chronology, and IFix substitution remains outside the static proof.
- The same hash-locked protocol audit discovers the generic LevelScript start
  policy from metadata method signatures, enum constants, and decoded native
  branch targets. It validates that an `Active`, unfinished
  `SameWithActive` script reaches the common internal `PreStart` transition
  without accepting any level/script/object id as a discovery input. This
  closes the start-policy question, not the mission/server source of `Active`
  state or cross-Story ordering.
- The audit also resolves `ManualStartLevelScript` fields through the current
  MetadataRegistration type table and validates the native
  `Execute -> TryGetLevelScript -> ManualStart -> PreStart` path. Serialized
  controls using the metadata-defined `CURRENT_LEVEL_ID` and
  `CURRENT_SCRIPT_ID` operands are therefore recovered as hosting-script
  self-targets for every matching row; no scene or script id participates in
  discovery. Promotion still requires an authored event-header link and adds
  no mission ownership or cross-Story order.
- A second general activation contract inventories every direct current-client
  `ManualStart` caller, validates the public state-notify application chain,
  and recovers the generic client request lifecycle. Exact metadata schemas,
  runtime field offsets, and decoded call sites prove `ManualStart` flag ->
  `PreStart` -> typed CS start request -> `PreStartActionRunning`; the runtime
  true/false request sites are both inside `UpdateRuntimeState`. The public
  network sender implementations each call `BaseNetworkSystem.SendMsg`, but
  have zero direct callers in the current AOT corpus, so indirect/IFix/server
  selection remains outside the contract.
  The same contract generically validates receiver timing: `Setup` registers
  the serialized trigger graph, and `UpdateRuntimeState` enables
  `TriggerActiveDuring.Active` while advancing from `ActiveBegin`. Mission
  Pipeline joins exact receiver header ids back to the original LevelScript;
  it never uses scene ids or filenames as rules. Active-phase receivers do not
  require the later ManualStart/Start transition. The same decoded state
  machine separates `SubLevelScript` from every other metadata-defined type.
  Joining the exact LevelData brief type proves that all 95 current receivers
  use `Enabled -> UpdateWithinActiveArea -> PreActive -> active=true ->
  WaitForStateActive`; no script-id exception exists. A bounded structural
  MemoryPack scan also decodes each script's top-level active-shape list without
  ids or filenames (86 sphere / 9 box), while the installed binary validates
  the active/outside-list state transitions. A complete direct-call census also
  separates the full-scene `SC_SELF_SCENE_INFO`/`LEVEL_SCRIPT_INFO` snapshot
  path from incremental state notifications and proves both public-state values
  are server-supplied; the other two direct setters only initialize state zero.
  The server-side selection rule, player position and playthrough-specific area
  result, server acceptance, event occurrence, mission ownership, and Story
  order remain unknown.
  The receiver frontier also performs a schema-key-driven census of every JSON
  record under the selected original structured-data root. It accepts only
  reviewed exact script-identity plus mission/quest-identity pairs in the same
  record, currently `bindScriptId + dungeonMissionId`; any new pair shape,
  parse failure, or missing corpus fails publication with a bounded diagnostic.
  Filenames, neighboring records, OCR, and overrides never create an edge.
  It proves that `InteractiveLogicChallengeStartPoint` resolves the typed
  `SubGameInstanceData` row by `m_subGameId`, reads `bindScriptId`, looks up the
  LevelScript, and calls `ManualStart`. Exact SubGame bindings are therefore
  interaction-start carriers. The public packet contains only scene, script,
  state, and completion fields, so neither path supplies mission ownership,
  server branch selection, or Story order.
- LevelScript task recovery is corpus-driven rather than keyed to individual
  scenes. The builder validates the installed binary/protobuf task contract,
  joins every decoded task condition to its exact `lt:p` and `lt:mp` LevelData
  properties, and scans only actual original MissionRuntime filenames for
  possible foreign-key tokens. Scene/script/task identity proves server-backed
  task lifecycle, but does not supply mission ownership or Story order.
- Mission Pipeline resolves exact native receiver playback gates generically
  through serialized `ActionHeader._validate` getter references. The resolver
  walks reusable AND/OR/NOT/ALL and comparison trees to exact leaves; unknown,
  missing, cyclic, and malformed children fail closed instead of receiving
  object-specific rules.
- Mission-state Story alternatives are projected corpus-wide from exact typed
  `CompareMissionState` / `GetMissionState` control paths. Complete serialized
  arms may cross nominal mission Story groups, but remain non-owning and add no
  chronology edge; original LevelScript, MissionRuntime, binary, and metadata
  files are attached with hashes.
- Native branch grouping is anchor-based rather than mission-filtered: once an
  exact event/branch contains a mission Story file, every exact Story-bearing
  arm is retained, including nominally external files. Split fan-outs require
  the current binary scheduler contract; all such cross-boundary rows remain
  non-owning and non-ordering and carry hashed original files.
- Story-anchored native branches are also expanded generically from the
  runtime-active original LevelScript action map. The typed control schema
  exposes every Split/IfElse/Switch slot, including active non-Story actions,
  inactive targets, runtime terminals, arm-exclusive actions, and shared
  downstream nodes. Runtime-mapping or topology mismatches fail closed with
  bounded source/hash diagnostics; no mission/object allowlist is used.
- MissionRuntime-to-receiver context joins are likewise corpus-driven and
  require the exact typed `(mapId, scriptId)` operand from the recursive
  objective condition tree. Flat script-id summaries cannot attach a mission.
  Exact matches publish related files as context only and never create
  ownership, activation, property-writer, or Story-order edges.
- Authored quest forks are recovered generically from normalized
  MissionRuntime predecessor graphs. The builder classifies main/auxiliary
  arms, guards, terminals, and shortest common descendants, attaches the exact
  hashed source file, and fails closed on unresolved arms. Story projections
  resolve variant MissionRuntime forks through globally unique quest identity,
  not filename conventions or mission-specific mappings. Each arm also expands
  to its sibling-exclusive reachable quest corridor and publishes every typed
  quest Story relation plus hash-checked original source files. Action types
  require the complete installed-binary ActionBase formatter audit; context
  relations remain non-owning, and OCR/manual order never participate.
- Shipped-Lua Story playback is likewise corpus-driven: the Lua consumer audit
  enumerates typed `GameAction` calls, exact literals, and simple
  `Tables.<name>` row-field flows. A table field resolves only when the current
  original table has one possible non-empty value; mission/quest ownership is
  admitted only from the same resolved row. Mission Pipeline validates Lua and
  table hashes and admits no case-folded match without a matching
  installed-binary case-resolution audit. The cinematic-queue runtime audit
  structurally discovers the native base/handle/payload contract, mapped
  one-handle dispatchers, and enqueue edge; handle branches are one runtime
  family rather than unresolved authored Story references.
- Reuse Timeline/reference outputs only when their original inputs did not
  change.
- The direct Story builder can take several minutes; allow 10–15 minutes for
  multi-language or forced recovery runs.

## Main WebUI builders

```bat
python scripts\verify_export_freshness.py
python scripts\story_builder\refresh_evidence.py
python scripts\story_builder\source_links.py
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\build_character_data.py --languages CN --default-language CN
python scripts\build_mission_pipeline_data.py
python scripts\build_gameplay_data.py
python scripts\build_progression_data.py
python scripts\build_projectile_data.py
python scripts\build_combat_relationships.py --languages CN
python scripts\build_economy_data.py --languages CN --default-language CN
python scripts\build_world_data.py --languages CN --default-language CN
python scripts\build_presentation_data.py --languages CN
python scripts\build_assets.py
python scripts\build_audio.py
python scripts\pack_webui.py
```

Story helpers live under `scripts/story_builder/`. Recovery audits live under
`scripts/story_recovery/` and are not all part of the canonical export.

Important Story components:

- `dialog_registry.py`: DialogIdTable registration.
- `video_bindings.py`: FMV/video definitions and attachments.
- `timeline_recovery.py`: Timeline evidence.
- `timeline_action_evidence.py`: typed action/control evidence.
- `mission_recovery.py`: mission and quest relationships.
- `build_source_story_gap_queue.py`: actionable source-only recovery queue.
- `story_recovery/build_levelscript_actionbase_tag_audit.py`: recovers the
  complete ActionBase MemoryPack formatter table from installed
  GameAssembly/metadata and refreshes the compact hash-pinned runtime name
  contract under `reports/mission_order/`.
- `story_recovery/build_callserver_callback_contract.py` and
  `build_callserver_callback_audit.py`: hash-pin the installed native
  `CallServer` possible-subexecutor contract, then recover every exact
  same-file callback-header control graph across the LevelScript corpus without
  mission, object, or Story allowlists.
- `story_recovery/build_cinematic_queue_runtime_audit.py`: repeatable installed
  metadata/GameAssembly audit that structurally discovers the cinematic handle,
  enqueue/producer call graph, and typed action-to-producer routes without
  per-object allowlists.
- `build_spaceship_story_content_audit.py`: exact typed spacecraft DialogTree
  and character profile-voice non-mission classification, refreshed by
  `refresh_evidence.py`.

## Updates

```bat
python scripts\build_updates.py
python scripts\build_updates.py --baseline-only
python scripts\build_updates.py --skip-asset-updates
python scripts\build_updates.py --skip-audio-updates
python scripts\build_updates.py --refresh-previous-export-baseline
```

Normal Updates scope includes exported Story/Text JSON, images, models, videos,
and decoded audio. Use `--full-export-scan` only for a broad audit. Never use
`webui/`, `reports/`, `memory/`, or `scratch/` as comparison roots.

## Assets and audio

`build_assets.py` creates the Assets tab indexes and compact Story-media lookup.
`build_audio.py` writes shared audio once under
`export_full/structured/Audio/shared/`, language voice under
`export_full/structured/Audio/<LANG>/`, and relinks playable conversation
audio.

Use `export_assets.bat --export-from-game` for installed-game image/model/
Material/CN-audio refresh. Asset modes, from narrowest to broadest, are
`--focused-assets`, `--default-assets`, and `--debug-assets`.

## Source graph

```bat
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
```

The default WebUI graph keeps only exact AssetMap source/PathID rows consumed
by material, shader, texture, and FMV edges. Full graph builds are for
investigation.

## Output locations

- `webui/data/`: generated browser payloads.
- `reports/export/`: export summaries, runs, and benchmarks.
- `reports/story/build/`: canonical Story build reports.
- `reports/story/recovery/`: recovery audits.
- `reports/mission_order/`: partial-order and gap reports.
- `reports/updates/`: Updates comparisons.
- `reports/assets/`: asset diagnostics.
- `reports/source_graph/`: SQLite graph and graph reports.

Put revisitable experiments in `scratch/<topic>/<task>/` and disposable work in
`tmp/<topic>/<run>/`. Do not add one-off scripts to `scripts/` unless they
become maintained WebUI or character-lab workflow code.

## Validation policy

During Story recovery, batch several independently validated edits before a
canonical rebuild. Prefer focused tests, direct probes, and
`--mission-pipeline-data-only` during iteration.

Validators must fail closed and report:

- validator and failed gate;
- affected mission or Story key;
- source path and relevant hashes;
- bounded expected versus actual values;
- deterministic failure details in structured data and CLI output.

Add tests for successful and representative failure cases when validator
behavior changes.
