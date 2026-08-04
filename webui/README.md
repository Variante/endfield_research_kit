# WebUI

`webui/` is a static browser for generated Endfield research data. It is the
primary supported user interface.

## Run

From the repository root:

```bat
.\export.bat
python serve.py
```

Reuse `http://127.0.0.1:8765/` if it is already running.

## Pages

- **Story:** recovered dialog, radio, SNS, cutscenes, options, media, and
  evidence.
- **Text Tables:** searchable localized table rows.
- **Gameplay:** curated character, weapon, ability, progression, economy, and
  world records.
- **Mission Pipeline (experimental):** quest DAG plus evidence-typed Story
  trigger chains.
- **Assets:** exported images, models, materials, video, and metadata.
- **Updates:** differences between previous and current exported game data.

Mission Pipeline, Characters, Progression, Combat & Projectiles, standalone
Combat, Factory, World, and Presentation are experimental and appear only with
`Show debug info`.

## Main files

- `index.html`: application shell.
- `style.css`: shared layout and media presentation.
- `app.js`: loading and Story rendering.
- `app_tree.js`: navigation, grouping, and filters.
- `app_labels.js`: shared labels and formatting.
- `reference.js`: Text Tables.
- `assets.js`: Assets.
- `updates.js`: Updates.

Generated payloads live under `webui/data/`; do not hand-edit them.

## Data layout

```text
data/manifest.json
data/lang/<LANG>/index.json
data/lang/<LANG>/conv/
data/lang/<LANG>/mission/
data/lang/<LANG>/reference/
data/mission_pipeline/
data/assets/
data/updates/latest.json
```

Manual runtime inputs live under `webui/overrides/`:

- `story_order.json`: complete user-managed mission order.
- `options.json`: manual option positions and responses.
- `narrative_videos.json`: explicit video attachment/suppression rules.

Rebuild Story data after editing overrides.

## Behavior contract

- Recovery issue and method filters stay visible in all modes.
- Debug panels and manual order controls are behind `Show debug info`.
- Reset returns to Story sort and preserves expanded mission groups.
- Disabling debug from a hidden page returns to a visible page and URL.
- Mission Pipeline distinguishes ownership, context, definition-only rows, and
  unresolved native playback.
- Its authored-structure panel expands every MissionRuntime quest fork into
  main/auxiliary arms, typed objective and failure guards, terminal state, and
  exact first common descendant. It links the hash-validated original runtime
  file and labels server-side arm selection as unresolved.
- Its native-boundary panel shows the generally discovered mission/quest
  identity+state application paths, the exact lifecycle identity flow, the
  absence of a client successor selector, and the hash-validated original
  `GameAssembly.dll` and `global-metadata.dat` sources. Each displayed quest
  fork also shows the binary-derived `StartQuest` boundary: objective-list
  reads, zero predecessor/flow reads, zero topology traversal calls, and both
  exact related original files. The same card exposes the whole-client
  topology-field census: verified direct `GetQuestInfo` callers, the deprecated
  predecessor-description reader, display-only flow comparator, main-path
  context/cache consumers, and zero topology-driven lifecycle calls.
  Predecessor forks remain topology rather than claimed server branch choice.
- Post-playback `CallServer` rows show their complete binary-decoded serialized
  contract and exact related `LevelScriptData` file, while keeping correlation
  labels and argument parameters explicitly non-owning.
- BlackBox recovery shells show the exact SubGame row, bound LevelScript,
  separate main/extra/fail task lanes, complete decoded task conditions,
  condition formulas, objective display keys, typed parent playback, and the
  complete serialized event/action graph. Ordered Branch sequences, Split
  fan-outs, conditional choices, loops, convergences, Story targets,
  runtime-shadowed duplicate-id records, and missing-slot normal terminals
  remain distinct from separate event roots and from parents
  that are definition-only. Task topology is never presented as a successor
  graph or Story order, and action edges never order separate event roots.
- Story-order panels attach compact original LevelScript graphs only through an
  exact native event-to-Story path. They show the related file and semantic
  control actions, active last-serialized runtime slots, and shadowed physical
  records without treating the rest of the file as mission chronology.
- Native branch cards show typed predicate operands when the current binary
  union, formatter field order, payload shape, and runtime consumer all agree;
  embedded root `GameCondition` unions and local getter references retain
  their nested type/operand details, while opaque or changed shapes remain
  visibly unresolved.
- Exact native receiver cards recognize the reusable `EncounterBase<T>` /
  `EncounterData` property contract structurally and show its validated
  LevelData host, LsmPtr module namespace, receiver LevelScript, and typed
  SpawnerConfig dependency. Module and receiver ids are kept distinct, zero
  spawners are labeled explicitly, and these remain non-owning with no branch
  or order edge.
- Exact native receiver cards also show generally decoded
  `ActionHeader._validate` playback gates. Predicate type, operands, local
  header/getter/action ids, recursive getter-node count/depth, and the original
  LevelScript file stay visible. AND/OR/NOT/ALL trees are rendered from typed
  child references while missing, cyclic, or unknown children fail closed;
  the UI labels them as receiver-local branches, never mission ownership,
  cross-Story order, or proof of a later server write.
- Receiver cards with decoded tasks show the binary-validated
  scene/script/task protocol identity, exact `lt:p`/`lt:mp` LevelData progress
  properties, and hashes for attached original binaries and data files. The
  panel keeps this server-backed task lifecycle separate from mission/quest
  ownership and scene-file ordering.
- Every receiver whose serialized start type is `SameWithActive` also shows
  the generic binary-validated `Active + unfinished -> PreStart` transition,
  the discovered runtime method/enum values, and exact binary/metadata hashes.
  The panel keeps the still-missing mission/server activation source and
  cross-Story order visibly unresolved.
- Receiver cards with a matching serialized current-context ManualStart row
  show the binary-validated `CURRENT_LEVEL_ID + CURRENT_SCRIPT_ID -> hosting
  script -> ManualStart -> PreStart` carrier, its authored event/action local-id
  link, native method addresses, and exact binary/metadata hashes. This is a
  local self-start edge only; mission ownership, branch selection, and
  cross-Story order remain explicitly unresolved.
- Every receiver card shows the binary-validated public state application path
  and its scene/script/state-only packet boundary. Cards with an exact typed
  SubGame binding additionally show the original-data
  `SubGame id -> bindScriptId -> LevelScript -> ManualStart` interaction
  carrier. Both panels attach current binary/metadata hashes while keeping
  mission ownership, server branch selection, and cross-Story order unresolved.
- Every receiver card also shows the binary-validated client start-request
  lifecycle: `ManualStart flag -> PreStart -> CS start request ->
  PreStartActionRunning`, including sender addresses, true/false runtime request
  arguments, and the zero-direct-caller boundary on the public network API.
  This remains the later Start lifecycle and does not promote the request path
  to ownership or ordering.
- Every exact receiver card now shows its original serialized header phase and
  the generic binary-validated `Setup -> ActiveBegin -> enable Active(0)` path.
  All 161 receiver headers are Active-phase, including validated runtime-
  shadowed maps. The 54 manual scripts therefore do not need ManualStart for
  receiver availability. Each card also joins its exact validated LevelData
  type to the generic binary selector. All 95 current receivers are non-
  `SubLevelScript` and visibly show `Enabled -> active-area gate -> PreActive ->
  active=true -> WaitForStateActive`. Each card also shows its directly decoded
  original sphere/box activation geometry and the binary-validated active/
  outside-list gate behavior. The UI still labels the source of Enabled,
  player position and playthrough-specific spatial result, server acceptance,
  event occurrence, mission owner, branch choice, and cross-Story order
  unresolved.
- Mission Pipeline opens source-bounded activation gaps in the order panel and
  shows exact ReadingPopUp/RichContent row identities for definition-only text
  files and
  lists exact recovered definition files, tables, non-owning LevelData context,
  and internal Timelines without promoting OCR or manual order to evidence.
- Quest diagnostics list the exact original-data files and decoded property or
  NPC-proxy record that bounds a non-owning co-membership; authored DialogTree
  branch context remains visible even when it cannot identify a unique trigger.
- Mission order is never inferred from registration, source-file order, or
  code addresses.
- World rows without an exported level remain unassigned.
- Identifier-only Combat ownership remains visibly inferred.

## Inline media

- `sns_emoji_*` renders as small inline emoji with no hover or modal.
- `sns_image_*`, `sns_sticker_*`, and related non-emoji media render at normal
  proportions.
- Hover and modal previews stay bounded by the viewport.

Useful fixtures:

```text
test_sns_emojicomment
test_sns_sticker
sns_topic_map02_lv005_12002
```

## Verification

After frontend changes:

1. Reuse or start the local server.
2. Confirm Story and Text Tables load.
3. Check normal and debug navigation.
4. Verify Mission Pipeline unresolved/definition-only labeling.
5. Check emoji, sticker, image, hover, and modal behavior.
6. Confirm no generated data contract changed unintentionally.

## Scope

Keep this README focused on frontend behavior. User setup belongs in the root
`README.md`, script contracts in `scripts/README.md`, and durable recovery
status in `memory/`.
