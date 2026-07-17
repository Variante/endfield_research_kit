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
- `src/features/mission_pipeline/`: debug-only experimental mission DAG and selected-quest client/server protocol trace backed by `data/mission_pipeline/`.
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

The normal navigation keeps Gameplay as the main semantic explorer. Mission Pipeline, Progression,
Combat & Projectiles, the retained standalone Combat graph, Factory, World, and
Presentation are deferred and available only when `Show debug info` is enabled;
turning debug off while one is active returns to Gameplay (or Assets from
Presentation). The explorers lead with a plain-language purpose while technical
graph terms, confidence rules, source provenance, and runtime limitations remain
available through expandable guidance.

- `Mission Pipeline` (debug-only, experimental): all currently exported
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
  browser follows Story's collapsible mission-type / mission hierarchy and
  natural mission-id ordering. Dragging anywhere on the graph pans without
  selecting a quest once the drag threshold is crossed; an unmodified mouse
  wheel zooms around the pointer. Quest cards show both the short HUD objective
  and the effective localized mission description (including quest-specific
  overrides). The selected-quest inspector links only Story files with a direct
  runtime reference or a uniquely resolved LevelData/NPC attachment; merely
  sharing a mission id is not enough to attach a file to every quest block.

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
