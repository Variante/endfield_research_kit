# WebUI

`webui/` is a static research browser over generated Endfield data. It has no
application build step: serve the repository and open the default local URL.

This file is the frontend contract: pages, routing, controls, layout, and the
shape of the `webui/data/**` JSON each page reads. Per-page recovery inputs,
evidence boundaries, and refresh commands live in
[`memory/webui/README.md`](../memory/webui/README.md); the shared export and
publication sequence in
[`memory/webui_recovery.md`](../memory/webui_recovery.md); commands and builder
ownership in [`scripts/README.md`](../scripts/README.md).

## Run

```bat
python serve.py
python serve.py 9000
```

Reuse `http://127.0.0.1:8765/` when it is already running. A custom port is for
an explicitly separate server.

`serve.py` serves the repository root and mounts the export roots, so a page
can link straight at extracted media:

| URL root | Serves |
| --- | --- |
| `/` | repository root; `/webui`, `/webui/`, and `/webui/index.html` redirect to the app |
| `/export_full/...` | the current export root |
| `/export_data/...` | raw `StreamingAssets/Data` and `Persistent/Data` files |
| `/export_previous/...` | the saved previous export's assets |

When present, root-level `endfield_paths.bat` supplies the current and previous
export mounts through `ENDFIELD_EXPORT_ROOT` and
`ENDFIELD_PREVIOUS_EXPORT_ROOT`. Explicit process environment values take
precedence; `WEBUI_PREVIOUS_EXPORT_ROOT` remains the server-specific override.

## Pages and routing

Eight tabs, in navigation order. `data-view` is the tab token in `index.html`
and the value of `document.body.dataset.activeView`.

| Page | `data-view` | Scope |
| --- | --- | --- |
| Story | `story` | Reconstructed dialog, SNS, radio, options, cutscenes, media, and evidence-typed order |
| Map | `map-recovery` | Authored world-space evidence with minimap, model, point, and water layers |
| Characters | `characters` | Identity groups, source evidence, related assets, and live overrides |
| Gameplay | `gameplay` | Characters, equipment, enemies, items, progression, skills, projectiles, assets, and sound |
| Audio | `audio` | Wwise Events/media, authored contexts, decoded playback candidates, and recovery state |
| Assets | `assets` | Exported images, models, materials, video, and metadata |
| Text | `reference` | Searchable localized table/reference rows |
| Updates | `updates` | Exported game-data changes between two complete versions |

Deep links are query parameters kept current with `history.replaceState`.
`#<view>` also selects a tab: the retired `#projectiles` falls back to
Gameplay, and any other unknown hash falls back to Story.

| Parameter | Selects |
| --- | --- |
| `?ui=` / `?uiLang=` | interface locale |
| `?lang=` | data language |
| `?story=` / `?conv=` | Story conversation key |
| `?asset=` | Assets entry by relative path |
| `?audio=` + `?audioKind=` | Audio record (`events` or a media shard) |
| `?gameplay=` + `?gameplayId=` + `?entry=` | Gameplay list, item, and sub-entry |

Factory, World, Presentation, Progression, the standalone Combat & Projectiles
page, and the Mission Pipeline page are retired; their useful progression,
projectile, and sound information lives in Gameplay. Mission Pipeline recovery
is a standalone Python workflow, and `webui/src/features/mission_pipeline/` is
not loaded by `index.html`.

## Frontend map

Load order, as `index.html` declares it:

| Files | Role |
| --- | --- |
| `index.html`, `style.css` | shell, page containers, shared layout and media presentation |
| `src/core/{namespace,dom,loader,storage,text,locale,paths}.js` | globals, DOM helpers, fetch/caching, persistence, text, locale, paths |
| `src/ui/{media_player,splitter,filters}.js` | shared media player, resizable splitters, filter panels |
| `app_labels.js`, `app_tree.js`, `src/features/story_triggers.js`, `app.js` | Story/Text labels, tree rendering, trigger evidence, Story page |
| `assets.js` | Assets page |
| `src/features/characters/{index.js,style.css}` | Characters view and runtime overrides |
| `src/features/gameplay/{labels.js,index.js}` | Gameplay datasets and sound players |
| `src/features/audio/{index.js,style.css}` | Audio evidence browser |
| `src/features/map_recovery/{index.js,style.css}` | Map view |
| `src/features/next_views.js` | shared page-bootstrap wiring |
| `src/features/reference/index.js` | localized Text Tables browser |
| `src/features/updates/index.js` | Updates page |

Generated data belongs in `webui/data/`; user-managed inputs belong in
`webui/overrides/`. Do not hand-edit generated JSON.

## Generated data

```text
webui/data/manifest.json
webui/data/lang/<LANG>/index.json
webui/data/lang/<LANG>/{actors,missions,search}.json
webui/data/lang/<LANG>/narrative_video_evidence.json
webui/data/lang/<LANG>/conv/*.json
webui/data/lang/<LANG>/mission/*.json
webui/data/lang/<LANG>/reference/**
webui/data/lang/<LANG>/characters/index.json
webui/data/lang/<LANG>/gameplay/**
webui/data/lang/<LANG>/gameplay/projectile_audio.json
webui/data/lang/<LANG>/gameplay/{sound_effects,combat_relationships}.json
webui/data/lang/<LANG>/audio/{index,events,media}.json
webui/data/lang/<LANG>/audio/media.NNN.json
webui/data/lang/<LANG>/audio/{event_details,media_details}/**
webui/data/lang/<LANG>/audio/scene_backgrounds.json
webui/data/gameplay/projectiles.json
webui/data/map_recovery/index.json
webui/data/map_recovery/maps/<levelId>.json
webui/data/map_recovery/render/*.{json,png}
webui/data/assets/{index,gameplay_refs,story_media,videos}.json
webui/data/updates/latest.json
webui/data/updates/characters.json
webui/data/story_order_ocr.json
webui/data/mission_pipeline/index.json
```

Builders may add compact sidecars, but each page must tolerate an absent
optional sidecar and display an explicit degraded state when the omission
matters. Schema changes must be coordinated with their frontend consumer.

### Ownership rules that are easy to get wrong

- `data/gameplay/projectiles.json` owns immutable projectile behavior and
  authored event hashes; the language-specific `projectile_audio.json` owns
  decoded media candidates. Gameplay joins them by projectile id, sound field,
  and unsigned event hash and writes no audio row back into the behavior
  payload.
- `data/assets/gameplay_refs.json` is Gameplay-owned: the `asset-refs` stage
  joins the current Gameplay index to the Assets-owned broad index. The Assets
  builder never writes this consumer-specific sidecar.
- `data/assets/videos.json` is an optional video catalog, absent unless
  published; the Assets page works without it.
- `data/story_order_ocr.json` holds OCR order proposals only. It is generated
  evidence and never the active order.
- `data/mission_pipeline/index.json` is read by the Story page for
  `storyCoverage.storyTriggerManifest` even though Mission Pipeline is not a
  page. Its absence is a degraded Story trigger state, not an error.

## User-managed inputs

`webui/overrides/` is hand-maintained input, and the only tracked JSON in the
tree. Four files are writable from the running app through `serve.py` (`PUT` or
`POST` to the same path under `/overrides/`, validated per file and written
atomically); the other two are edited offline. `serve.py` refuses any write
outside `webui/overrides/`, and export tools never replace these files.

| File | Owner page | Writable from the app |
| --- | --- | --- |
| `overrides/story_order.json` | Story | yes |
| `overrides/character_merges.json` | Characters | yes |
| `overrides/character_name_overrides.json` | Characters | yes |
| `overrides/audio_notes.json` | Audio | yes |
| `overrides/options.json` | Story options | no |
| `overrides/narrative_videos.json` | Story media | no |

## Shared behavior

- Normal navigation exposes exactly the eight pages above.
- The top bar owns the data-language select (`#language`), the interface-locale
  select (`#ui-language`), and the shared `Show debug info` toggle
  (`#show-debug`).
- Debug state controls raw source blocks, recovery evidence, manual Story-order
  tools, and unresolved ownership details. Story issue and recovery-method
  filters remain visible in normal mode.
- Every list page shares one layout: a search box (`#*-q`), a collapsible
  filter panel (`#*-filter-panel`, `#*-filter-toggle`) of named filter
  sections, a reset button, shown/total counts, a resizable splitter, and a
  detail pane on the right.
- All search boxes accept case-insensitive regular expressions. Queries are
  split on whitespace with OR semantics, so `^npc_`, `boss|elite`, and `map0[12]`
  are useful examples; malformed expressions are treated as literal text.
- Missing optional data is a visible unavailable/degraded state, not an empty
  success state. Authored definition, recovered relation, inferred ownership,
  runtime observation, and user annotation stay visibly distinct.
- Filters, keyboard focus, modal behavior, and large result sets must remain
  usable on narrow and wide screens.

## Story

Controls: search, sort (`sort-story`, `sort-natural`, `sort-lines-asc`,
`sort-lines-desc`), filter sections `basic`, `kind`, `media`,
`recovery-method`, and `type`, the issue filter (`#story-issue-filter`),
`#reveal-current`, and the toggles `Show empty rows` (`#show-empty`),
`Show raw JSON / text sources` (`#show-raw`), and `Show raw tags`
(`#inline-tag-mode`). `Endministrator variant` (`#gender-variant`,
Female/Male) switches dialogue text, voice, images, video, and gender-specific
cutscenes, and stays synchronized with Gameplay.

- Reset returns to Story sort and default filters while preserving expanded
  mission groups.
- Source/debug blocks, Timeline evidence, cutscene diagnostics, and order-edit
  controls (`#story-order-editor-row`, `#story-order-save-status`) remain
  debug-only.
- `sns_emoji_*` renders as ordinary inline emoji without hover or modal
  preview. Other SNS images and stickers keep their natural proportions with
  bounded hover and modal previews.
- Cutscene rows can show an automatic `未使用` badge only when the current
  build's complete, non-degraded playback-carrier census finds no exact or
  uniquely case-insensitive consumer. Case collisions and incomplete scans
  remain unresolved and unmarked. This evidence badge is separate from the
  user-managed `possiblyUnused` Story-order override.
- `overrides/options.json` manual option coverage adds a separate filterable
  override tag. Story keeps the generated option-evidence issue and its count
  unchanged instead of replacing source-state classifications such as
  unregistered table-only placement.
- `overrides/narrative_videos.json` controls inline video attachment,
  suppression, and optional audio inheritance.

Story evidence typing, ordering, and reconstruction gaps belong to
[`memory/webui/story.md`](../memory/webui/story.md) and
[`memory/webui/story_recovery.md`](../memory/webui/story_recovery.md).

## Characters

Characters merges table, Story, and asset identities while retaining source
provenance. Merge and name overrides are live inputs written through `serve.py`
and do not require a rebuild. Debug-only controls must not leak into normal
page navigation.

When available, `data/updates/characters.json` supplies optional version-change
badges and filters. Added or modified ids join the constituent ids and aliases
of the already-recovered identity group; deleted ids are read-only
previous-version snapshots. The sidecar never changes automatic or manual
grouping, naming, evidence, or override behavior, and its absence leaves the
Characters page fully usable without change badges.

## Gameplay

Filter sections: `basic`, `kind`, `rarity`, `job`, `character-property`,
`weapon-type`, `equipment-type`, and `enemy-type`, plus search, reset, and
`#gameplay-reveal-current`.

Gameplay owns character progression, equipment, enemies, skills, projectiles,
assets, and compact sound players. Evidence labels distinguish exact authored
ownership from family-, animation-, or identifier-inferred placement.

- Exact `chr_NNNN_token` namespaces are published even without a
  `CharacterTable` row, labeled namespace-only, leaving availability,
  progression, runtime use, and playable status unproven.
- Enemy level selectors show only authored level points; missing levels are not
  interpolated. Positive authored skill cooldowns are shown at the selected
  skill level.
- Enemy born-Buff cards expose exact BuffData lifecycle, stacking, trigger,
  keyed-value evidence, attribute modifiers, and applied tag ids. An unmapped
  ID keeps its raw value and explains on hover why the current serialized
  registry did not resolve it.
- Decoded action chains show the gated event name and decoded fields, including
  actions nested under If/Else branches and common `TargetSettings` fields even
  when the enclosing action is partial. Unresolved unions, selectors, and
  complex payloads stay visibly unresolved.
- Projectile templates, spawned behavior, and playable-skill ownership remain
  separate relations. Character-skill and enemy SFX players are collapsed
  compactly with inferred ownership labeled, while raw identity, matching, and
  unresolved candidates are debug-only. Shared animation Events are labeled as
  global Wwise graphs unless a stronger owner edge exists.
- Native enum names, tag names, and gated event names disappear when the
  selected build gate does not validate; the authored rows remain.

Page evidence limits are owned by
[`memory/webui/gameplay.md`](../memory/webui/gameplay.md), what the datasets
establish by
[`memory/game_data/gameplay_semantics.md`](../memory/game_data/gameplay_semantics.md),
and per-action layouts by their `scripts/game_data/buff_*_native.json`
contracts.

## Audio

Audio keeps four layers separate and claims only the available one:

1. authored Event or media identity;
2. Wwise graph relation and possible media leaves;
3. authored consumer/trigger context;
4. observed runtime execution or selected branch.

### Layout and playback

- In a selected record the playable-media block is rendered first, immediately
  below the detail heading and before Details, manual notes, and the longer
  facts/evidence sections.
- Expanded files load with their waveform visible. A group of more than 20
  possible files keeps lazy collapsed players and loads each waveform only when
  that file is expanded; candidate player cards otherwise stay expanded and
  materialized.
- The default purpose-priority sort and recovery filters put unknown-purpose
  Events/media ahead of partial and known-purpose records. A direct Story-line
  binding is a terminal known-purpose state and is not part of the
  investigation queue.
- Each Event and media record accepts a note in its detail pane. The user must
  explicitly select `Save note`; typing alone never writes the override or
  updates search/list state. Notes are keyed by language and record identity,
  persist through `overrides/audio_notes.json`, join the existing text search,
  and show their first line beside the record filename in the list. They are
  user annotations, not generated game-data evidence.
- Identity-only collapsed groups exist for character and enemy namespaces
  (`chr_*`, `au_chr_*`, `au_actor_<token>_*`, `au_monster_<token>_*`, `au_`)
  and are never merged with skill or animation SFX.
- The Audio overview loads `data/lang/<LANG>/audio/scene_backgrounds.json` as a
  compact scene catalog with validated and missing object-index sources,
  partial coverage kept visible, and scene filters by scene id, mission id, or
  Event. Event chips navigate to the existing Audio Event detail; the catalog
  duplicates no Wwise branches or media.

### Detail sections

All of these are authored serialized joins: `Direct node effects` from
`postProcessSummary.effectNodes`; `Serialized effect chain` (direct node slots
before each serialized leaf-to-root Bus path, at most 64 stages per row with
explicit truncation); `Serialized RTPC controls` and
`Serialized State overrides` (at most eight curve points each, marking
truncation); Bus-control, ducking, and User-Defined Aux send references
resolved by Bus ID against the unique Bus catalog, so the media shard
duplicates no large authored payload;
serialized media-edge types and selection paths (`directSound`, `layerChild`,
`randomAlternative`, `switchCandidate`, sequence/music edges) with root Action
IDs; `trigger_contexts.json` `mediaRefs` joins; non-playback Action payloads
(SetState/SetSwitch, GameParameter ranges and fade policy, Stop/Pause/Resume,
Seek, value/filter actions, exception buses, FX slot bypass); and the lazy,
debug-only AudioCue AST. An unsupported tail stays visibly fail-closed with its
offset and reason.

### Status vocabulary

Rendered verbatim in details, search, and filters:

- identity and naming: `eventIdentityStatus=grammarHashPreimageNameRecovered`
  with `eventNameSourceKind=grammarHashPreimage` and the head/tail sibling
  counts that admitted the name, `ownerKind=npc`, and the physical
  `wwise/unknown` path.
- category and ownership: the physical `audioCategory` is preserved beside a
  separately recovered semantic category (`SFX`, `voice`, `UI`, `ambience`,
  `control`, `music`, `cue`) and a searchable coarse ownership (scene
  environment, scene object, animation, gameplay component, interaction, UI,
  voice system, mission narration). A mixed known-category join stays
  unclassified, and a generic scene emitter keeps scene ownership without being
  forced into a category.
- authored fields and scenes: `monoBehaviourAudioIdField` roles
  (`componentSoundSpawn`, `componentHitCallback`, finish/state, water/particle,
  or the generic serialized-field boundary with an audio-key hint) plus
  `componentLayout`; `sceneOwnershipStatus`, `sceneContainmentStatus`,
  `sceneId`, `sourceName`, `sourcePath`, and
  `conflictingPrefabInstanceIdentityJoins`.
- routing and control: `noExplicitOutputBusSerialized`,
  `controlCatalog.staticRtpcAlignment` with its six canonical `AU_RTPC_*` names
  (`AU_RTPC_CINE_CTRL_VOL_AMB`, `...VOL_MU`, `...VOL_SFX`,
  `...IS_MUTE_BY_SDK_WEBVIEW`, `...IS_SURROUND_CHANNELS`,
  `...GLOBAL_VOL_MASTER_IOS_WORKAROUND`) and
  `postProcessSummary.gameParameterNameEvidence`, and the custom/internal
  numeric targets `0x1802`/`0x1804`.
- AudioCue AST: `exprType`, `exprType=3`, `exprType=8`, `runtimeCueVariable`,
  `compositeOpaque`, `childrenLimit`.

### Storage and degraded state

- Shared SFX/music and language voice stay in separate storage roots. Repeated
  media IDs preserve every physical occurrence and package provenance.
- Direct Story-line binding, authored context, Event-only relation, and unknown
  placement are mutually exclusive generated media states.
- Role, Event, and category coverage counts come from generated summaries and
  are never hard-coded in the frontend.
- When native inputs are missing or mismatched, authored Audio rows remain
  visible; only build-locked callsites, mappings, and addresses disappear, with
  the unavailable state shown explicitly. The gated groups are the interactive
  and Snapshot state Events, enemy and character voice callsites, Story
  `dialogId` lifecycle hooks, and the `EnemyTriggerVoiceAction`
  voice-type-to-trigger-key mapping.
- An unverified, missing, or mismatched offline capture bundle stays a degraded
  diagnostic and adds no runtime binding.

What each of these states refuses to claim is the UI-facing evidence boundary
in [`memory/webui/audio.md`](../memory/webui/audio.md). The Wwise chain itself
-- bank format, HIRC object graph, curves, plug-in parameter layouts, naming
coverage, native hooks -- is owned by
[`memory/game_data/audio_overview.md`](../memory/game_data/audio_overview.md)
and the `audio_*` files beside it. Changing per-build row and occurrence counts
belong in `reports/`.

## Map

Map is a normal page immediately after Story. It plots authored Unity X/Z
coordinates and only draws a background when the image and its world bounds
share an explicit transform.

### Generated contract

- `data/map_recovery/index.json` lists maps, their exact `regionKey`, the
  current default map, and compact counts.
- `data/map_recovery/maps/<levelId>.json` owns markers, quest points, facets,
  mission/file evidence, minimap metadata, and one recovered render manifest.
- `data/map_recovery/render/` owns generated minimap composites, elevation,
  surface, point, height-mask, and water PNGs plus their manifests.
- Shared-scene identity comes only from the directly addressed
  `LevelConfig/<levelId>.json` streaming path. Similar names are not evidence.
- Streaming-instance sidecars use schema 2 and one `meshes` array per entity
  base. They feed static render layers only and are not duplicated as clickable
  map nodes.
- Every point layer owns its height mask as `pointCloudOverlay.heightMask`;
  there is no top-level mask fallback.
- The browser derives stitched bounds from the loaded background rectangles;
  region bounds are not duplicated in index or payload metadata.

### Panel and layer controls

- A map opens as clean geography. The resizable left panel is a three-column
  map/task/object-filter tree whose outer body owns scrolling for all three
  columns; map status sits with the task column instead of a separate header
  panel, and the complete JSON/file inspector is also resizable.
- The plain third column combines entity, quest, story, and mission filters
  with minimap, elevation, surface, water, point, and point-height controls
  without an inner layer container; there is no separate bottom filter dock.
- Each available raster layer occupies one row with a visibility checkbox and
  its own opacity slider. Layer opacity persists while switching maps and does
  not reset when that layer is temporarily hidden.
- Authored floor overlays are discovered by hovering their covered area and
  cycled locally by clicking; there is no global floor slider.
- Entity size is independent from map zoom. Layer opacity and the two-thumb
  point world-Y filter change presentation only.
- The bottom-centre range switch defaults Map01/Map02 to the selected zone.
  `All zones` explicitly loads and stitches every Wuling or Valley-IV member;
  switching back releases the cached sibling payloads as well as removing them
  from the rendered surface.

### Navigation and markers

- Physical level variants that share one authored place are one map entry and
  remain selectable as map items in the task column; their per-level payloads
  and inspector JSON are retained, and only the duplicate navigation entry is
  collapsed. Unnamed single-mission maps use the localized mission code/name,
  and authored cross-map Story continuations are explicit navigation links.
- Map01, Map02, and config-proven shared blackbox scenes stitch by exact
  `regionKey`; dungeon maps with a source-art dependency remain independent.
  Minimap/model/water rectangles and markers all use X/Z with image top at +Z,
  and `needInverseXZ` applies the evidenced quarter-turn consistently.
- Quest routes are grouped by mission and ordered by authored `questOrder`.
  Shared-file or shared-script relation webs are not rendered.
- NPC proxies with explicit `npcProxyDialogAttachments` expose their owning
  mission and quest ids as selectable phases. The selector does not derive an
  order from proxy ids, registration order, or coordinates.
- Selecting a mission keeps missionless level-world entities available through
  the ordinary type/floor filters; compact maps enable all recovered object
  types by default.
- Enemy, device, scenery, and travel markers use distinct glyphs, and authored
  grenade towers retain their Factory/Combat/Model evidence. Enemy labels
  resolve through `EnemyTemplateDisplayInfo` plus localized text; exact reading
  points use the generated Story title instead of their internal `text_*` key.
- Unresolved evidence gets its own default-hidden layers: empty `int_empty`
  shells in an unresolved-empty-slot layer, and unresolved script-target
  references in a candidate layer, rather than being presented as understood
  interactions.

### Inspector

- Strong identity links stay separate from weak spatial or mission context, and
  proximity is never upgraded into ownership.
- Opening `WorldEntityRegistry.json` from a registry-backed point resolves its
  exact world id or script-id/slot pair, jumps to the matched row and paired
  brief-info array index, and highlights the focused excerpt.
- When a map node has a generated Story conversation, that conversation is the
  normal reader-facing file and placement, registry, script, and other evidence
  files stay behind `Show debug info`.
- Map-wide files and weak file links are debug-only unless the file has an
  exact generated Story deep link; disabling debug also closes any file viewer
  whose link is no longer visible.

Which spatial evidence may become a marker, what a slot action binding proves,
and how each render layer earns its evidence grade are owned by
[`memory/webui/map.md`](../memory/webui/map.md) and
[`memory/game_data/story_carriers.md`](../memory/game_data/story_carriers.md).

## Assets and Text

- Assets: search plus filter sections `basic`, `category`, `type`, `source`,
  and `sort`. The detail pane owns image/video/text preview with a selectable
  preview background, an OBJ/FBX model canvas with mesh stats, material,
  reference and related-asset lists, the original JSON/script source,
  copy-path and download actions, and `?asset=` deep links.
- Text: search plus filter sections `basic`, `group`, and `source`. Known row
  shapes render as rows; every row keeps its raw JSON beside the rendered view,
  so an unsupported shape stays searchable instead of being silently dropped.

## Updates

Updates displays the comparison of two complete export roots: WebUI-facing
exported text plus image, model, video, and decoded audio assets, never a
change under `webui/`, `reports/`, `memory/`, or `scratch/`.

Controls: search plus filter sections `basic`, `category`, `extension`,
`status`, and `sort` (path, status, size delta, line delta), the
added/modified/deleted summary counts, the run metadata line, and an explicit
truncation note.

```bat
.\build_updates.bat OLD NEW
```

## Verification

Build commands and their contracts live in
[`scripts/README.md`](../scripts/README.md); which workflow owns a changed
input is in [`memory/webui_recovery.md`](../memory/webui_recovery.md). The
shortest loop for frontend work is:

```bat
python scripts\verify_export_freshness.py
.\export.bat
python serve.py
```

The page smoke-test checklist is in
[`memory/webui_recovery.md`](../memory/webui_recovery.md). Its Story media step
uses the fixtures `test_sns_emojicomment`, `test_sns_sticker`, and
`sns_topic_map02_lv005_12002`.
