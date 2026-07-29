# WebUI Notes

The `webui` frontend is intentionally small and static. It reads generated JSON
from `webui/data/`, serves exported media/audio from `export_full/`, and keeps
heavyweight recovery work in the Python builders.

## Browser Files

- `index.html` and `style.css`: shared shell, tabs, and layout.
- `src/core/`: small dependency-free browser utilities used by every tab.
- `src/ui/media_player.js`: shared audio/video control wrapper.
- `app_labels.js`: UI text, labels, and shared story formatting helpers.
- `app_tree.js`: story filters, grouping, sorting, and sidebar tree rows.
- `app.js`: story data loading and conversation rendering.
- `src/features/gameplay/`: curated weapon, character, skill, and talent browser backed by `data/lang/<code>/gameplay/index.json`.
- `src/features/progression/`: authored progression/reward relationship browser backed by `data/lang/<code>/progression/index.json`.
- `src/features/projectiles/`: exact-payload projectile inspector backed by `data/gameplay/projectiles.json`.
- `src/features/combat/`: evidence-labelled relationship explorer backed by `data/lang/<code>/gameplay/combat_relationships.json`.
- `src/features/economy/`: factory/economy browser backed by `data/lang/<code>/economy/index.json`.
- `src/features/world/`: static authored-world browser backed by `data/lang/<code>/world/index.json`.
- `src/features/mission_pipeline/`: experimental mission DAG and selected-quest client/server protocol trace backed by `data/mission_pipeline/`.
- `assets.js`: exported asset browser, shared view routing, and preview panel.
- `src/features/reference/`: raw localized text-table browser.
- `src/features/updates/`: focused exported text JSON and asset update browser.

## Current Scope

- `Story`: language switch, search, foldable filters, a Storyline filter for
  mission/story buckets, Media chips for entries with videos, non-emoji images,
  SNS stickers, or emoji, recovered game-data story-order sorting with compact
  evidence badges in mission lists, conversation detail, summaries,
  option groups, line-order notes, raw source traces, and inline media
  rendering for SNS/content images. Recovery issue/method filters stay visible
  in every mode. Raw source/debug blocks, mission timeline evidence, cutscene
  debug panels, and manual order-edit controls are gated behind the `Show debug
  info` toggle so normal browsing stays compact. Resetting filters returns to Story sort while
  preserving expanded mission groups, and gender variant selection is a header
  toggle. The current chrome uses a light neutral palette with muted teal and
  orange accents while keeping category badges softly color-coded. Narrative
  video blocks show the best
  playable active-gender/source variant for each distinct video, without
  counting hidden duplicate format/source variants as extra videos. Story
  search includes option ids as well as line ids/text. Option
  groups recovered from Runtime Jump route tracks preserve option-specific
  route lines, merge shared suffix lines once, and render branch-owned
  follow-up option groups as flat siblings in the owning branch chain instead
  of nesting them inside compact branch rows. Timeline-inferred groups with
  strict `trunkClipOptionIndex` evidence render their per-option candidate
  lines below each option prompt in the same branch-column flow, outside the
  option prompt shell. Single-option follow-ups render
  their recovered next lines as flat line siblings beside the option prompt in
  that same chain, using compact regular-line styling inside branch columns and
  full regular-line styling after the branches merge. When route outcomes prove a
  follow-up group is shared by every option, that shared-continuation evidence
  takes precedence over a single `after` anchor and the group resumes once
  below the option columns. Shared continuation lines resume once after
  branch-local prompts. Branch-owned dialog lines render once in the option path
  and are removed from the trunk even when
  recovered Timeline order disagrees with numeric line suffix order. DialogIdTable
  recovery chips expose runtime trunk line refs and runtime option refs in
  their tooltip when that evidence is available. Automatic option-placement
  issues distinguish table-key matches, original line-number gaps,
  end-of-scene fallback, and truly unknown positions; recovered groups remain
  inline at their `after` line. Known option placement or
  inferred-response gaps can be covered for WebUI display only through
  `webui/overrides/options.json`; edit it and refresh the browser,
  no Story rebuild needed. Affected option groups or rows show a manual
  override tag. The Story index carries compact per-issue option group/option
  targets so Recovery Issue counters are evaluated after runtime overrides:
  fully covered issue classes move to `Manual override`, partial coverage stays
  in the original issue class plus `Needs manual override`, and source recovery
  methods remain visible as provenance. Mission Timeline Recovery shows the
  quest map track, LevelScript spatial candidates, source-script hints, and
  source-backed scene edges. Timeline action evidence from recovered
  AnimeStudio managed references appears behind `Show debug info` as compact
  line-order agreement, action-kind counts, and per-line staging chips. Cutscene chips now include compact identifying labels, and cutscene
  detail panels expose placement evidence plus variants, paths,
  metadata, videos, audio events, and actor labels to make individual
  cutscenes easier to identify. When `scripts/build_audio.py` has linked
  decoded audio, dialog/cutscene lines with `audioSrc` and recoverable
  cutscene audio events render WebUI audio controls with draggable seek bars;
  audio-only lines remain visible even when empty-text rows are hidden. Audio
  links accept root-served `/export_full/...`, `export_full/...`, or
  `structured/Audio/...` forms and normalize them to the served export route.
  playable Story and Updates videos use the same draggable progress control.
- Narrative videos without a resolved story key are emitted as standalone
  `video` story files grouped by mission. Videos that resolve to dialog,
  cutscene, remotecomm, or another story file also attach to that file;
  standalone video rows sort beside the attached file. Timeline / playable
  evidence supplies authored inline placement when available. Manual
  attachments and false-attachment suppressions live in
  `webui/overrides/narrative_videos.json`; attach rules can set `audioFrom`
  to copy source cutscene audio events during audio relink. Videos stay
  available as standalone `video_*` rows after the Story builder is rerun.
- `人物` / `Characters`: searchable character and NPC names with source
  evidence, generated by `python scripts/build_character_data.py`. It includes
  every `npcName_*` entry from `TextTable.json`, playable `CharacterTable`
  rows, named `NpcTable` and `SNSChatTable` rows, the generated Story actor
  registry, and aggregated exported asset filename evidence for `_actor_`, `_npc_`,
  `_major_npc_`, and `_npc_major_` markers. Asset evidence retains matching
  file counts and representative paths without treating filename tokens as
  localized names. The left pane has the same collapsible filter panel,
  horizontal filter resizer, and vertical pane splitter used by the other
  inspector pages; its result list scrolls independently from the evidence
  detail pane. Records with the same localized display name and the same set
  of discovered known names are shown as one group containing every matching
  identity and its evidence. Unknown-only `???` / `？？？` values do not split
  an otherwise matching group, while conflicting known names do. The complete
  filtered name list is rendered immediately without a `Show more` batch.
  Asset-only tokens are resolved against existing table-backed identities first
  (including suffix matches such as `weixidong`), then Story identities, before
  falling back to a raw filename token.
- `Gameplay`: curated weapon, equipment, character, enemy, and usable-item
  records from structured
  game tables, generated by `python scripts/build_gameplay_data.py`. Weapon
  rows use `ItemTable.name` for the localized display/file name, follow
  `WeaponBasicTable.weaponSkillList` into `SkillPatchTable`, and show localized
  effect text, blackboard values, upgrade checkpoints, stat checkpoints,
  breakthrough costs, and talent bound templates. Equipment rows show localized
  part/domain/formula context, display attributes, suit effects, material costs,
  and per-property stat curves. Character rows use
  `CharGrowthTable.skillGroupMap` as the displayed skill source and show linked
  `SkillPatchTable` action/scaling data, skill level-up costs, grouped
  break/equipment/attribute/talent nodes, profession, element, default weapon
  links, level checkpoints, capped character stat checkpoints, break-stage caps,
  breakthrough costs, and potential unlocks. Enemy rows show authored variants,
  level stat curves, abilities, damage/resilience scalars, attribute modifiers,
  born buffs, tags, drops, model/AI ids, and display classifications. Usable-item
  rows show localized descriptions, stack/type metadata, use duration/category,
  buff or skill actions with blackboard values, and fixed/probable chest rewards.
  Gameplay filters include kind,
  job, rarity, group, and text search. Gameplay entries with a matching
  `wiki_*` Story page render a Story link, and those Story wiki pages render a
  return link back to the Gameplay entry.

The normal navigation exposes Gameplay and Mission Pipeline. Characters, Progression,
Combat & Projectiles, the retained standalone Combat graph, Factory, World, and
Presentation are deferred and available only when the top-right `Show debug info`
switch is enabled; turning debug off while one of those deferred views is active
returns to a normal page. The explorers lead with a plain-language purpose while technical
graph terms, confidence rules, source provenance, and runtime limitations remain
available through expandable guidance.

- `Mission Pipeline` (experimental): all currently exported
  `MissionRuntimeAsset` graphs as deterministic ranked
  DAGs. Predecessor and quest-state-condition edges remain authored evidence,
  while every predecessor transition passes through a visible server-authority
  gateway. Selecting a quest shows the native asynchronous protocol sequence:
  `SC_QUEST_STATE_UPDATE` activation, local condition callbacks,
  `CS_UPDATE_QUEST_OBJECTIVE` / `SC_QUEST_OBJECTIVES_UPDATE`, optional
  `CS_FINISH_DIALOG` / `SC_FINISH_DIALOG`, authoritative completion/failure,
  and the opaque server successor decision. `flowIndex` is displayed only as
  an authored lane tag, never as proof of exclusivity. The curated `e7m3`,
  `c16m3`, `e2m5`, and `e7m4` overlays distinguish parallel joins, active AND
  monitors, repeatable outcomes, and a persisted cinematic result. The mission
  summary also shows native-proven global-variable and spawner exchanges with
  exact protocol fields, asynchronous direction/role, and a boundary-only tag;
  these rows are not attached to quests without a separate ownership proof.
  The mission browser follows Story's collapsible mission-type / mission hierarchy and
  natural mission-id ordering. Dragging anywhere on the graph pans without
  selecting a quest once the drag threshold is crossed; an unmodified mouse
  wheel zooms around the pointer. Quest cards show both the short HUD objective
  and the effective localized mission description (including quest-specific
  overrides). Quest-card badges and the selected-quest inspector separate
  `Story -> Quest` condition dependencies, `Quest -> Story` native action
  triggers, and non-directional scoped context. Each connection retains its
  relation, phase, action slot when applicable, confidence, and source path,
  and links directly to the recovered Story file. The generated trigger-route
  manifest renders the proven chain as quest/mission ownership, server message,
  native event, LevelScript, native action, and Story terminal steps. Unresolved
  playback keeps an explicit ownership gap, while definition-only files remain
  visibly distinct. Exact, build-pinned CutsceneRoot playback aliases render as
  `Story root -> native playback action -> Story file` debug routes with their
  own corpus count. An alias remains non-owning unless an independently
  connected route terminates at that exact root through a native playback
  action; when it does, the UI renders the complete composed owner route and
  removes the target from that mission's unassigned queue. The composition
  never implies relative Story order. Build-pinned candidates rejected by native resolution remain
  route-free and, with `Show debug info` enabled, render on the unassigned Story
  card as recovery boundaries rather than graph edges. Every recovered
  serialized event occurrence renders in its own causal lane with its event
  summary and selector fields, listening
  LevelScript/header, transport boundary, and complete native action chain;
  multiple lanes are alternatives or distinct occurrences rather than an
  inferred sequence.
  Each lazy mission payload also embeds the strict source-only Story partial
  order: reduced causal edges, topological frontiers, cyclic components, quest
  forks/joins, cross-scene option routes, and intra-dialog option branches.
  Exact serialized event-to-action path prefixes add order only when one Story
  action is literally traversed before another; shared event roots without a
  prefix remain unordered. Divergent native `Split`, `IfElseAction`, and
  `SwitchInt` paths expose their Story-bearing arms, and convergence is shown
  only when every observed arm reaches the same later local ID. Each
  conditional group also exposes its exact event selector and the recovered
  PureGetter or inline-Param predicate; getter class-only evidence remains
  visibly weaker than decoded operands.
  Attachments require authored
  runtime references or bounded LevelData, LevelScript, variant-runtime, or
  unique NPC-proxy evidence; mission-id co-membership and spatial proximity are
  not enough to attach a file to a quest block. LevelData context specifically
  requires a fully parsed member-22 `LevelScriptBriefData` dictionary entry,
  its repeated final script id, contiguous entry framing, and exact dictionary
  count; the UI labels this as an asset host rather than logical quest ownership.
  Typed activity-stage rows add exact quest-level host chips without attaching
  Story. Action-only DialogTrees reached by exact quest-state LevelScript chains
  render as separate Open UI terminals with their panel/activity parameters;
  they are not normalized into `misc_dlg_*` conversations and do not affect
  Story coverage.
  A broad LevelData shell can also be scoped without reading its filename when
  typed `MissionAreaTrackingInfo.missionAreaId` resolves through
  `MissionAreaTable.subDataParentId` to a root key in that same validated
  dictionary and every authored root agrees on one mission. Shared roots stay
  unresolved.
  The complete member-22 shell can also scope a sibling playback script when
  every exact MissionRuntime, typed MissionArea, and mission-shaped asset
  anchor in that container agrees on one mission. This is shown as
  authoritative asset-shell context, never as a quest trigger.
  Typed `EntityTrackingInfo` also supplies a narrow client-navigation join:
  the local script/entity slot must resolve through the native global-id path
  and one aligned `WorldEntityRegistry` row. The UI distinguishes an exact
  tracked interactive `type_id` from a typed Story control path merely stored
  in that same script, displays both tracked and event slots, and labels both
  as context rather than playback, chronology, or a server exchange. Raw
  file-wide strings and unrelated getter records never create this relation.
  Mission summaries also show ambient envTalk context through two exact,
  non-owning paths: typed quest tracking to an envTalk-carrying NPC proxy, and
  atmospheric switcher state conditions joined to an envTalk cluster through
  one same-level active group containing the cluster's complete NPC set.
  Partial, cross-level, ambiguous, or identity-mismatched joins are rejected.
  These rows explain navigation or world-state availability only; they do not
  enter the mission Story coverage denominator and do not claim playback,
  ownership, order, completion, or a server exchange.
  Non-script tracking may also resolve one counted world-interactive record
  only when component 94 exactly co-carries the mission id, `Dialog(1)`, and
  Story id and every registry/table/template mirror agrees. The current SM1
  row is labeled navigation/configuration context and gives its reachable
  DialogTree child only a possible authored route; it is not ownership,
  guaranteed playback, completion, chronology, or a server exchange.
  Interactive Story aliases require the fully decoded native two-map
  `InteractiveTable` and template `int_narrative_mission`. When the binary also
  proves a tracked slot through `TravelPoleBegin -> EntityCompare -> IfElse ->
  RaiseCustomLevelEvent -> unique Story listener`, the UI exposes the complete
  producer/listener route while keeping a server-placeholder objective opaque.
  Exact MissionArea/Leader-trigger geometry appears only after level-scoped
  table resolution, union/member checks, key/slot equality, and EOF-bounded
  trigger-body decoding; it is local context rather than server completion.
  Mission-shell context can also
  come from exact authored SNS mission-id agreement, explicit FocusMode
  mission/radio fields, uniquely scoped LevelScript actions, or a serialized
  black-screen playable whose Timeline parent chain resolves through the exact
  `DialogBriefInfo.usedDialogTimelineIds` field to its parent dialog and either
  a typed playback host or one unique direct parent-dialog mission context.
  Multi-quest parents remain mission-shell context. Native playback whose trigger remains unknown is shown as
  unresolved evidence, not attached to an arbitrary quest.
  Exact client-global-variable event paths and typed `WaitForNpcProxyReady`
  paths may add mission-shell context when their original-data consumers agree
  on one mission. Shared quest candidates remain visible, and the UI explicitly
  says that no request/response payload was decoded.
  Exact EOF-bounded `Play3DRadio` payloads may add mission context when
  `useNpcProxy` is true and the emitter proxy has one same-scene typed
  MissionRuntime owner. The UI shows the proxy and candidate quest context but
  does not claim that the quest starts playback. The complete typed TravelPole
  entity-compare/custom-event route may also inherit one authoritative
  validated LevelData shell; this adds the three second-zipline cutscenes to
  `e0m0` without inventing quest chronology.
  Typed narrative-mask actions embedded in a dialog TextAsset can also attach
  an exact black-screen Story file through their serialized LangKey. The UI
  shows the parent dialog, typed action class/path, asset PathID, evidence tier,
  and explicitly labels the block as local presentation with no server
  exchange. Multiple parent dialogs, literal stage directions, and missing
  parent scope fail closed.
  Typed `DialogLeftSubtitleActionData.text1..text4` uses the same strict parent
  scoping but renders as its own local left-subtitle relation. It must not be
  presented as black-screen playback, audio playback, quest placement, or a
  protocol exchange.
  If the same black file occurs under multiple parent dialogs, accepted and
  unresolved uses are shown together through complete/partial scope fields;
  one resolved parent never hides another unresolved native containment.
  When native ownership stops at a same-file event, the unresolved row includes
  the normalized MemoryPack event/action tags, authored event payload or trigger
  slot, and exact `ActionHeader.nextId` / `ActionBase.nextId` / typed
  `Split` / `IfElseAction` control-path count. This is an unscoped native
  LevelScript subgraph, not a mission or quest attachment.
  Event names come from the complete installed-build 230-tag ActionHeader
  formatter table and are applied only to proved `headerList` records, avoiding
  collisions with overlapping ActionBase and PureGetter tag spaces. Exact
  current-build `SwitchInt` case/default traversal now gives every remaining
  native-playback row a serialized event-owner path.
  Exact BattleSignal receivers additionally render their original
  SkillData/BuffData producer actions as a local producer → literal signal →
  listener → playback → Story chain. The current payload has 13 receiver nodes
  and 21 producer routes for 20 unique actions. Every card says that the route
  sends no server request and expects no return, and that signal identity does
  not prove a producer, mission, or quest owner.
  Mission-state dependency cards also expose task/condition ids and offsets.
  A same-script taskMap condition is explicitly marked as not control-path
  linked, dependency-only, and non-owning.
  Native receiver activation cards additionally expose every fully decoded
  task-map condition and its exact entity, spawner, dialog, destination,
  property, stage, monster, or combine operand. The current receiver corpus has
  25 fully decoded task-map scripts, 32 tasks, and 55 conditions. These rows
  describe evaluation/completion requirements only; the UI must not present
  them as activation, mission ownership, or execution order.
  One receiver script is also named by a typed MissionRuntime objective. Its
  card exposes the exact mission/quest/objective and condition type as a
  `Quest observer` boundary row with ownership, activation, and Story playback
  all false; observing a LevelScript property does not prove that the quest
  starts the playback or that playback writes the property.
  Each condition also shows an exact authored operand source when available:
  current-script or logic-id WorldEntity rows, same-level LevelScripts,
  MissionArea/SpawnerConfig rows, or same-receiver Story keys. The current
  payload resolves 46 conditions to 53 source rows and finds zero exact typed
  MissionRuntime consumers for those operands. Source identity is debug
  context, not a mission edge.
  Task labels also expose an exact typed
  `CheckLevelScriptTaskFinished(scene, script, task)` consumer if one appears;
  the current receiver payload has zero.
  Where exact level/script/task keys agree, the same rows also show
  `ScriptTaskExtraInfoTable` title keys and SubGame main-task ids. The current
  corpus has 13 task-info joins and ten SubGame task joins; every matched
  SubGame row lacks `dungeonMissionId`.
  Receiver cards also show exact `DungeonTable.sceneId` / SubGame context:
  `18` receiver scripts and `14` Story files share `6` authored dungeon
  scenes, for `40` context placements. Only `7` placements are the SubGame's
  exact `bindScriptId`; the other `33` are explicitly labeled sibling scripts.
  Quest, mission-state, and prior-challenge unlock rows are availability
  prerequisites only and never become Story ownership, activation, or order.
  Nine sibling receivers additionally show the typed
  `DungeonSubGameData.dungeonMissionId` mission shell. The card retains
  `no mission owner`; the shell mission identifies the SubGame, not a different
  LevelScript's Story playback.
  A separate mission-lifecycle section shows exact NPC accept dialogs and
  explicit `NpcProxyEx.missionId` context. A collapsed `Unassigned Story`
  section keeps all remaining same-owner mission scenes visible without
  guessing a quest; cross-mission attachments are removed from that remainder.
  Mission sidecars are emitted for all exported MissionRuntime graphs, including
  variants without a standalone Story group, and client-action inspection
  follows the authored `_nextID` chain. Native addresses describe the installed
  build's fallback implementation; IFix-dispatched hotfix behavior may differ.
  The current CN coverage audit connects 4,065 of 5,273 unique Story files
  across 4,361 mission placements; 1,208 remain unlinked, including 153 with
  exact native playback but no decoded mission/quest trigger. OCR, manual
  overrides, and observed gameplay do not change these counts.

- `Combat & Projectiles` (debug-only, deferred): 310 exact decoded projectile templates grouped by
  their resolved character/enemy sender. Exact exported ownership edges are
  direct; derived skill-family and unique character/enemy identifier matches
  are labelled inferred, and unsupported/ambiguous records remain unresolved. Each
  record combines its sender, named skill, and bounded Combat links with
  source identity,
  collision geometry, duration/range, targeting, 331 movement-mode records,
  curves/Bezier controls, 536 assigned effects, alert behavior, and seven
  sound-hash fields. Byte structure is exact for observed variants; inferred
  enum/hash meanings remain visibly qualified.
- `Progression`: 9,836 authored roots joined to 15,691 typed nodes and 37,970
  direct relations. Character levels/breakthroughs/skills/talents/potentials,
  weapon curves/costs/breakthroughs/talents, equipment stages, item use and
  obtain paths, rewards, probable reward entries, drop pools, and wiki enemy
  drops retain raw values plus table/row/path provenance. This is static
  configuration, not live availability, account state, probabilities, or an
  optimal upgrade plan. The root list renders at most 200 rows per page and
  high-degree relation groups expand 60 rows at a time.
- `Combat` (debug-only standalone graph): 106 character/enemy roots joined to 5,138 nodes and 7,000
  evidence-labelled relationships across abilities, selectors, buffs,
  projectiles, effects, audio, and assets. This includes all 162 byte-proven
  AbilityEntity inherited prefixes and 833 direct managed-component RID links;
  135 character/enemy identifier matches remain visibly inferred, and the
  guarded opening through `useFrameTick` separates five matched root-component
  fields from six qualified metadata-order scalars. All 162 exact 92-byte
  `surroundingConfig` records are included, with 14 linked movement mirrors and
  10 non-consuming next-boundary rotation mirrors; enum/hash meanings remain
  qualified and bytes from `followMountPointConfig` onward are excluded. Direct
  and inferred edges remain separate. The view also includes 68 exact-consumed TargetSettings
  records proven reachable from curated character component graphs, plus two
  finder and two validator RID links; six avatar-template records without
  Gameplay roots are counted but not assigned. Raw authored values remain
  inspectable, and the view does not claim evaluator order or a final runtime
  combat formula.
- `Factory`: 392 recipes, 116 machines, 71 technologies, 658 referenced items,
  logistics and utility configuration, 29 shops/711 goods, 69 activities, and
  3,315 endpoint-valid typed relations. Relation panels expose navigable recipe,
  machine, technology, shop-good, activity, and available item links. These are static authored relationships, not live
  throughput, availability, or account state.
- `World` (debug-only, deferred): 21,778 entries and 22,411 evidence-labelled relations, including
  15,083 deduplicated world entities, 523 interactives, 1,601 NPC proxies, 413
  spawners, 186 referenced enemies, 207 levels, 6 maps, 3,658 level-script
  references, and authored audio/model links. Mirrored StreamingAssets and
  Persistent instances retain compact source provenance; coordinates describe
  authored placement, not live spawn or simulation state. The sidebar groups
  records by authored level ID and shows localized level names. The selected
  level's coordinate-bearing records render on a bounded, sampled SVG X/Z map;
  global registry objects without an exported level ID remain explicitly
  unassigned instead of being guessed from their coordinates. The list renders
  200 rows at a time so the 21k-entry corpus does not rebuild tens of thousands
  of DOM nodes on each filter change.
- `Presentation`: 3,084 curated roots, 7,452 nodes, and 16,857 endpoint-valid
  relationships across model configs/prefabs, model-view controllers, bounded
  asset entities, model/material/texture assets, shader-backed materials,
  animation configs/states/clips, and presentation-linked effects. Direct and
  inferred evidence remain separate; generic low-level Unity nodes, runtime
  renderer choice, animation transitions, effect timing, and shader behavior
  are intentionally outside the payload.
- `Assets`: exported image/model/video/JSON file search, source tag filters,
  metadata, raw links, related files, and previews where the browser supports
  them.
- `Text`: raw localized rows from `data/lang/<code>/reference/`, with
  source/table filters and on-demand table loading.
- `Updates`: latest change summary from `data/updates/latest.json`, generated
  by comparing WebUI-facing exported text JSON and exported image/model/video
  assets plus decoded audio between saved/current export roots, never generated
  WebUI files. Build it from the repo root with `build_updates.bat`, or compare
  arbitrary extracted roots by passing `--previous-export-root OLD`,
  `--export-root NEW`, and `--refresh-previous-export-baseline` to that wrapper.
  `build_updates_by_patch.bat --check` is detection-only, while its default
  apply mode stages changed VFS exports, rotates archive/current safely, and
  invokes the Updates-page builder after publication.

## Data Layout

- `data/manifest.json`: language list and build stats.
- `data/lang/<code>/index.json`: lightweight story tree entries only.
- `data/lang/<code>/actors.json`, `missions.json`, and `search.json`: lazy
  sidecars for display names and full-text search.
- `data/lang/<code>/conv/` and `mission/`: conversation and mission payloads
  loaded on demand.
- `data/gameplay/projectiles.json`: language-independent exact projectile
  inspector payload.
- `data/lang/<code>/progression/index.json`: language-scoped typed progression,
  reward, drop, obtain, and item-use relationship graph.
- `data/lang/<code>/gameplay/combat_relationships.json`: compact combat graph
  with confidence/evidence labels.
- `data/lang/<code>/economy/index.json`: curated factory and economy records and
  typed relations.
- `data/lang/<code>/world/index.json`: deduplicated static world entries,
  authored placement fields, source provenance, and typed relations.
- `data/lang/<code>/presentation/index.json`: bounded model/material/animation/
  effect graph built from the current local source graph, with caps, omissions,
  evidence confidence, and degraded-state metadata.
- `data/mission_pipeline/index.json` and `data/mission_pipeline/missions/*.json`:
  language-neutral lazy mission topology, condition gates, protocol metadata,
  and native-evidence overlays generated by
  `python scripts/build_mission_pipeline_data.py`. Mission names and objective
  text are merged from the selected language's existing Story sidecars.
  With `Show debug info` enabled, the Story page reuses the index's
  `storyCoverage.storyTriggerManifest` to show a compact trigger on every file
  row and a full evidence route for the selected file. Normal Story mode does
  not load or display this trigger evidence. Exact native
  event/action paths remain distinct from context-only mission ownership;
  condition, context, dependency, definition-only, and unknown rows are not
  presented as playback triggers. Typed `SubGameInstanceData`
  mission-to-bound-LevelScript rows are shown as a
  separate runtime-shell layer and never imply a quest or Story attachment.
  Their cards show `gameId`-keyed start/stop requests and asynchronous
  enter/start/complete/reward/leave server pushes from the installed
  GameMechanics protocol.
  The current native proof is explicitly scoped to lifecycle cleanup:
  `WorldChallengeGame.SendQuit` resolves the row's `bindScriptId`, manually ends
  the LevelScript when required, and then requests stop. OCR, manual, and
  gameplay cross-references cannot create graph edges.
  Missionless rows are still useful: when the same `bindScriptId` occurs on an
  exact decoded native Story-playback action, the global boundary panel shows a
  missionless `SubGame -> script -> playback -> Story` node. These nodes remain
  outside mission-connected Story coverage. Exact quest/mission-state unlock
  prerequisites are labeled as SubGame availability context and never as
  playback ownership or activation. Dashed edges show only exact non-
  owning cross-references from the activity-stage and GameMechanic condition
  tables; naming and blank association fields remain invisible.
  The same boundary panel separately renders exact serialized runtime-receiver
  nodes for unlinked native playback. The current CN payload has 158 nodes
  organizing all 153 exact-native unlinked Story files across 182 placements.
  Each card shows the
  listener script, exact selector fields, transport boundary, and linked Story
  files with `no mission owner`; these are not added to mission-connected
  coverage. A narrow original-data HP chain promotes only
  `radio_gm02m20_9/_18` to the `gm02m20` mission shell through a unique
  same-level SpawnerConfig, while explicitly retaining local/no-server and
  no-quest semantics.
  DynamicScene mission-control identity matches are shown in the same
  boundary area as candidate-only cross-references. Exact numeric
  `IdComp.logicId == LevelScript scriptId` equality can expose a mission/quest
  state condition beside a Story-playing LevelScript, but the two current
  native systems resolve those identities through separate registries.
  One current row has stronger local evidence:
  `map02_lv001/10100282001` explicitly targets the same DynamicScene id with
  `ShowSceneDecorationNew(..., false)` immediately after `dlg_c27m3_6` on the
  same serialized slot-80001 trigger chain. The card shows that typed target
  and shared local path, while separately stating that the mission condition
  to trigger-header activation edge remains missing.
  Accordingly these rows retain `storyBinding: false`,
  `orderEvidence: false`, unresolved ownership, and zero graph edges.
  An optional `missionRuntimeTrace.v1` bundle can be published with
  `--runtime-trace-bundle`. The WebUI renders captured event/action/playback
  routes, active-quest context, and per-session sequence/fork/merge evidence as
  an observed overlay. These rows are visually and structurally separate from
  authored Story connections: the builder adds no graph edge and explicitly
  records `ownershipPromotion: false` and `orderPromotion: false`.
- `data/lang/<code>/narrative_video_evidence.json`: timeline-backed video to
  WebUI conversation evidence. These rows require recovered
  `BeyondFMVPlayableAsset` / Timeline sources, including gameplay cutscene
  playables from AnimeStudio `json_by_type/MonoBehaviour`; heuristic filename
  matches are not recorded as proof.
- `export_full/recovered/AnimeStudio-cli/timeline_action_evidence.json`:
  builder-side dialog Timeline action evidence from AnimeStudio
  `$animestudio.recoveredManagedReferences.RefIds`. Conversation payloads only
  keep a compact debug slice under `_debug.timelineActions`; the full file is
  the audit source for action-flow line order agreement and per-line action
  class/layout counts.
- `export_full/structured/Audio/<code>/index.json`, shared decoded audio under
  `export_full/structured/Audio/shared/`, and language voice `.wav`/`.wem`
  files: optional audio generated by `scripts/build_audio.py`. Conversation
  payloads keep the per-line `audio` id and gain `audioSrc` only when a
  decoded file exists; ResponsiveDialog/AIBark fallback lines can also keep
  `AudioDialog.path` evidence as `audioPaths`/`audioPath` for relinking.
  Cutscene `audioEvents` gain `audioFiles` only when Wwise bank metadata links
  the event to decoded media. Story rebuilds run a skip-decode audio relink
  automatically for languages with decoded audio already present.
- `overrides/story_order.json`: user-managed Story sort order. Each
  `missions.<mission>.order` array is the complete file order for that
  mission, and the WebUI treats this override as the only order source in
  `按剧情排序` mode. `export.bat` leaves the file untouched. The OCR pipeline
  writes its proposed order to `data/story_order_ocr.json`; it does not update
  this override. The Story sidebar can save row moves or toggle a mission lock.
  `missions.<mission>.locked: true` freezes a mission so
  OCR proposal generation and browser-side save logic preserve the saved list exactly.
- `data/lang/<code>/reference/`: Text table payloads; persistent rows may share
  streaming payloads or use small overlay files for changed rows.
- `data/lang/<code>/gameplay/index.json`: curated Gameplay tab payload generated from structured tables such as `WeaponBasicTable`, `CharacterTable`, `CharGrowthTable`, and `SkillPatchTable`. Entries include `storyWikiKey` only when the current Story index has the matching wiki page.
- `data/lang/<code>/characters/index.json`: merged character/NPC name catalog
  with per-name and per-identity table, Story, and exported-asset evidence.
  Exported paths on the debug-only Characters page deep-link to the matching
  Assets-page entry.
- `data/assets/story_media.json`: compact Story inline image/video lookup using
  the same `entries` shape as the full asset indexes. The full
  `data/assets/index.json` remains for the Assets tab.

## Inline Media Rules

- SNS emoji assets such as `sns_emoji_*` are rendered as regular inline emoji.
  They stay inline and do not open hover popovers or the full-screen modal.
  Their resolver only uses exact or emoji-family sprite matches; if a matching
  emoji sprite is absent from `story_media.json`, the tag remains unresolved
  instead of borrowing numbered sticker or SNS decoration assets.
- EnvTalk emoji-only rows such as `envEmoji_common_*` render their line-level
  `emoji` fields from the Unity emoji prefab aliases and recovered
  RectTransform layer data in `story_media.json`. Recovered `AnimationClip`
  enter curves drive the initial alpha flicker and squash/stretch when the
  row scrolls into view, and replay on hover/focus. Standalone prefab variants
  are normalized to the same visual scale as the bubble-backed common emoji.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and matching
  `cg_image_*` assets should render with their normal image proportions rather
  than the compact emoji treatment. Exact non-emoji SNS media should not borrow
  numbered sticker, decoration, or emoji fallbacks.
- When a generated line has both an inline `<image=...>` tag and the matching
  `image`/`images` metadata, the inline render is the canonical display; the
  below-line media strip should not repeat the same asset, including when the
  inline tag display is switched to raw text.
- Inline image popovers and the modal preview should stay inside their visual
  border and the viewport.

## Explicit Non-Goals

- no runtime graph atlas or binding explorer in the frontend
- no mission editor, runtime simulator, or claim that the client-visible DAG
  contains the server's hidden successor-selection policy; Mission Pipeline is
  a read-only evidence viewer
- no local decoded-data or raw config browser tabs
- no broad frontend-side recovery workbench; the existing `Show debug info`
  toggle only exposes generated evidence/debug blocks needed to audit the
  current Story view

If one of those views becomes useful again, rebuild it intentionally instead of
letting the browser grow around recovery experiments.
