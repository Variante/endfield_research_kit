# WebUI

`webui/` is a static research browser over generated Endfield data. It has no
application build step: serve the repository and open the default local URL.

This file is the frontend contract: pages, routing, shared behavior, and the
shape of the `webui/data/**` JSON each page reads. Each page module's header
comment carries its detailed control and rendering contract. Per-page recovery
inputs, evidence boundaries, and refresh commands live in
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
| `/api/stores*` | read-only Data-page store API ([`store_browser.py`](../scripts/webui/data_inspector/store_browser.py)) |

When present, root-level `endfield_paths.bat` supplies the current and previous
export mounts through `ENDFIELD_EXPORT_ROOT` and
`ENDFIELD_PREVIOUS_EXPORT_ROOT`. Explicit process environment values take
precedence; `WEBUI_PREVIOUS_EXPORT_ROOT` remains the server-specific override.

## Pages and routing

Eight tabs, in navigation order. `data-view` is the tab token in `index.html`
and the value of `document.body.dataset.activeView`.

| Page | `data-view` | Scope | Behavior contract |
| --- | --- | --- | --- |
| Story | `story` | Reconstructed dialog, SNS, radio, options, cutscenes, media, and evidence-typed order | `app.js` |
| Map | `map-recovery` | Authored world-space evidence with minimap, model, point, and water layers | `src/features/map_recovery/index.js` |
| Characters | `characters` | Identity groups, source evidence, related assets, and live overrides | `src/features/characters/index.js` |
| Gameplay | `gameplay` | Characters, equipment, enemies, items, progression, skills, projectiles, and assets | `src/features/gameplay/index.js` |
| Text | `reference` | Searchable localized table/reference rows | `src/features/reference/index.js` |
| Audio | `audio` | Wwise Events/media, authored contexts, decoded playback candidates, and recovery state | `src/features/audio/index.js` |
| Assets | `assets` | Exported images, models, video, and metadata | `assets.js` |
| Data | `data-inspector` | Files list over the export stores, loose and undecoded export files, and decoded datasets, plus a SQL console | `src/features/data_inspector/{stores,index}.js` |
| Updates | `updates` | Exported game-data changes between two complete versions | `src/features/updates/index.js` |

`recovery` is one more, debug-only tab revealed by `Show debug info`
(`src/features/recovery/index.js`, data from
`python -m scripts.webui.recovery.build_recovery`). It shows block volume and
each file type's L1-L4 recovery state, keeping recovery internals out of normal
navigation. The volume bar shows inventory composition, never the fraction
recovered; states are scoped declarations, not numeric progress; a missing or
older payload shows an explicit rebuild state.

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
| `?inspectDataset=` + `?inspect=` | Data page, Files mode: the selected decoded record (dataset and record id) |
| `?dataMode=` + `?dataRoot=` + `?dataStore=` + `?dataGroup=` + `?dataName=` (+ `?dataQ=`, `?dataField=`, `?dataStatus=`, `?dataFolder=`, `?dataTag=`, `?dataSort=`) | Data page mode (`files`, `sql`; the retired `decoded` opens `files`), export (`previous`, omitted for current), selected sources (repeated `dataStore`: `unity`, `game-files`, `loose`, `undecoded`, `decoded`), selected groups (repeated `dataGroup=<source>:<group>`; an unqualified group belongs to `dataStore`), the selected store row, search, and the repeated decoded filters and order; build with `WebUI.dataPageUrl` / `dataPageUrlForRel` |

Factory, World, Presentation, Progression, the standalone Combat & Projectiles
page, and the Mission Pipeline page are retired; their useful progression and
projectile information lives in Gameplay. Mission Pipeline recovery is a
standalone Python workflow, and `webui/src/features/mission_pipeline/` is not
loaded by `index.html`.

## Frontend map

Load order, as `index.html` declares it:

| Files | Role |
| --- | --- |
| `index.html`, `style.css` | shell, page containers, shared layout and media presentation |
| `src/core/sprites.js`, `sprite_worker.js` | registers the service worker that renders Sprite images; the first visit reloads once when it takes over |
| `src/core/{namespace,dom,loader,storage,text,locale,paths}.js` | globals, DOM helpers, fetch/caching, persistence, text, locale, paths |
| `src/ui/{media_player,splitter,filters,facets,pagination}.js` | shared media player, resizable splitters, filter chips and panel toggle, declarative facet filters, list pager |
| `app_labels.js`, `app_tree.js`, `src/features/story_triggers.js`, `app.js` | Story/Text labels, tree rendering, trigger evidence, Story page |
| `assets.js` | Assets page |
| `src/features/characters/{index.js,style.css}` | Characters view and runtime overrides |
| `src/features/gameplay/{labels.js,loadout.js,index.js}` | Gameplay datasets, loadout calculator, and detail rendering |
| `src/features/audio/{index.js,style.css}` | Audio evidence browser |
| `src/features/map_recovery/{index.js,style.css}` | Map view |
| `src/features/next_views.js` | shared page-bootstrap wiring |
| `src/features/reference/index.js` | localized Text Tables browser |
| `src/features/updates/index.js` | Updates page |
| `src/features/recovery/{index.js,style.css}` | debug-only Recovery progress page |
| `src/features/data_inspector/{index.js,stores.js,style.css}` | Data page: `stores.js` owns the mode switch, deep links, and the Files/SQL modes; `index.js` is the decoded-dataset source (catalog, matching, row markup, record viewer) |

Generated data belongs in `webui/data/`; user-managed inputs belong in
`webui/overrides/`. Do not hand-edit generated JSON.

**Facet filters.** `src/ui/facets.js` (`WebUI.facets`) is the one model for a
list page's chip groups: a page declares its groups once and the model owns
active values, chips, counts, `(n)` badges, matching, reset, and URL/storage
persistence. Several chips in one group are OR, groups combine with AND, and an
empty group does not constrain. Every list page uses it; Map's layer checkboxes
and Recovery are not filter groups. The header comment of `facets.js` is the
API and page-convention contract.

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
webui/data/lang/<LANG>/audio/conv/{index,<key>}.json
webui/data/gameplay/projectiles.json
webui/data/map_recovery/index.json
webui/data/map_recovery/maps/<levelId>.json
webui/data/map_recovery/render/*.{json,png}
webui/data/assets/{index,gameplay_refs,story_media,table_owners,videos}.json
webui/data/data_inspector/index.json
webui/data/data_inspector/datasets/<datasetId>/{index,records.*}.json
webui/data/updates/latest.json
webui/data/updates/characters.json
webui/data/recovery/index.json
webui/data/story_order_ocr.json
webui/data/mission_pipeline/index.json
```

Builders may add compact sidecars, but each page must tolerate an absent
optional sidecar and display an explicit degraded state when the omission
matters. Schema changes must be coordinated with their frontend consumer.

### Ownership rules that are easy to get wrong

- `data/gameplay/projectiles.json` owns immutable projectile behavior. The
  language-specific `projectile_audio.json` and `sound_effects.json` remain
  generated recovery sidecars, but Gameplay does not load or render them;
  audio presentation stays on the Audio page until the ownership model is
  better understood.
- `data/assets/gameplay_refs.json` is Gameplay-owned: the `asset-refs` stage
  joins the current Gameplay index to the Assets-owned broad index. The Assets
  builder never writes this consumer-specific sidecar.
- `data/lang/<LANG>/audio/conv/<key>.json` is Audio-owned and merged by Story
  at load; Story's own `conv/*.json` never carries voice.
- `data/assets/videos.json` and `data/assets/table_owners.json` are optional;
  the Assets page works without them.
- `data/story_order_ocr.json` holds OCR order proposals only. It is generated
  evidence and never the active order.
- `data/mission_pipeline/index.json` is read by the Story page for
  `storyCoverage.storyTriggerManifest` even though Mission Pipeline is not a
  page. Its absence is a degraded Story trigger state, not an error.
- `data/data_inspector/**` is local recovery output, excluded from the
  published archives; its envelope is owned by
  [`contract.py`](../scripts/webui/data_inspector/contract.py).

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
  sections, a reset button, shown/total counts, a resizable splitter, a
  paginated left list with a persisted custom 1-10000-items-per-page input
  (1000 by default; 50/100/200/500/1000 are suggestions), a direct page-number
  input that clamps to the first or last page, and a detail pane on the right.
  Filtering and sorting return to the first page. Story and Map keep their
  specialized hierarchical navigation instead of flat-list pagination.
- All search boxes accept case-insensitive regular expressions. Queries are
  split on whitespace with OR semantics, so `^npc_`, `boss|elite`, and `map0[12]`
  are useful examples; malformed expressions are treated as literal text.
- Missing optional data is a visible unavailable/degraded state, not an empty
  success state. Authored definition, recovered relation, inferred ownership,
  runtime observation, and user annotation stay visibly distinct.
- Native enum names, tag names, and other build-locked labels disappear when
  the selected build gate does not validate; the authored rows remain.
- Filters, keyboard focus, modal behavior, and large result sets must remain
  usable on narrow and wide screens.

## Page contracts

Each page's full control list and rendering rules are in the header comment of
its module (table above). The rules below are the ones other documents and
pages depend on.

### Story

- Reset returns to Story sort and default filters while preserving expanded
  mission groups.
- Source/debug blocks, Timeline evidence, cutscene diagnostics, and order-edit
  controls are debug-only; issue and recovery-method filters are not.
- `sns_emoji_*` renders as ordinary inline emoji without hover or modal
  preview. Other SNS images (`sns_image_*`) and stickers (`sns_sticker_*`) keep
  their natural proportions with bounded hover and modal previews.
- The automatic cutscene `未使用` badge needs a complete, non-degraded
  playback-carrier census; it is separate from the user-managed
  `possiblyUnused` order tag. Manual option coverage adds a separate override
  tag and never replaces the generated option-evidence issue.
- Voice comes only from the Audio page's `audio/conv/` sidecars; without an
  Audio build the page shows no voice.
- `Endministrator variant` switches text, voice, images, video, and
  gender-specific cutscenes, and stays synchronized with Gameplay.

Evidence typing and ordering belong to
[`memory/webui/story.md`](../memory/webui/story.md) and
[`memory/webui/story_recovery.md`](../memory/webui/story_recovery.md).

### Characters

Merge and name overrides are live inputs written through `serve.py` and need no
rebuild. The optional `data/updates/characters.json` adds version-change badges
and filters only; it never changes grouping, naming, evidence, or overrides.

### Gameplay

Gameplay owns character progression, equipment, enemies, skills, Buffs,
projectiles, and assets; audio is not attached. Detail content renders flat.
Skill damage rows are authored setup: each conditional formula badge (normal
Hp route, AtkScale, BreakingAttack, Poise input) appears only while its own
selected-native audit validates, never substitutes stored level values for
runtime results, and leaves the raw setup plus one note when unavailable. The
Loadout view computes final attributes only from a validated
`attributeCalculation` (`loadout.js`). Evidence limits:
[`memory/webui/gameplay.md`](../memory/webui/gameplay.md) and
[`memory/game_data/gameplay_semantics.md`](../memory/game_data/gameplay_semantics.md).

### Audio

Audio keeps four layers separate and claims only the available one: authored
Event or media identity; Wwise graph relation and possible media leaves;
authored consumer/trigger context; observed runtime execution. Status fields
render verbatim in details, search, and filters; the token vocabulary is listed
in the header comment of `src/features/audio/index.js`. Notes are written only
on an explicit `Save note`. Missing or mismatched native inputs remove only
build-locked callsites, mappings, and addresses, with the unavailable state
shown. What each state refuses to claim is in
[`memory/webui/audio.md`](../memory/webui/audio.md); the Wwise chain is in
[`memory/game_data/audio_overview.md`](../memory/game_data/audio_overview.md).

### Map

Map plots authored Unity X/Z and draws a background only when the image and its
world bounds share an explicit transform. Generated contract:

- `data/map_recovery/index.json` lists maps, their exact `regionKey`, the
  default map, and compact counts; `maps/<levelId>.json` owns markers, quest
  points, facets, mission/file evidence, minimap metadata, `mapMark`
  annotations with `mapMarkCoverage`, and one render manifest; `render/` owns
  generated minimap composites, Terrain byte previews, elevation, surface,
  point, height-mask, and water PNGs plus manifests.
- Shared-scene identity comes only from the directly addressed
  `LevelConfig/<levelId>.json` streaming path. Streaming-instance sidecars use
  schema 2 with one `meshes` array per entity base.
- Every point layer owns its height mask (`pointCloudOverlay.heightMask`), and
  region bounds are derived in the browser from loaded background rectangles.
- Proximity is never upgraded into ownership; weak spatial or mission context
  stays separate from identity links, and non-Story evidence files stay behind
  `Show debug info`.

Marker eligibility and render-layer grades:
[`memory/webui/map.md`](../memory/webui/map.md) and
[`memory/game_data/story_carriers.md`](../memory/game_data/story_carriers.md).

### Assets and Text

- Assets lists images, video, OBJ, and FBX, not exported JSON: every such
  document is a Data-page store row, and a material links to its Data-page
  document. The optional `Table owner` fact requires an exact whole-stem match
  in an asset-bearing field.
- Sprite images are crop documents over their textures, still linked as
  `.../game/Unity/Sprite/<name>.png`; `serve.py` answers with the crop
  document and `sprite_worker.js` renders it pixel-identical to AnimeStudio.
  Without the worker (no secure context) Sprites do not display.
- Text keeps every row's raw JSON beside the rendered view, so an unsupported
  shape stays searchable. Maintained `fields` link only to a resolved row in a
  table present in the Text index; unresolved references are never linked.

### Updates

Updates shows the comparison of two complete export roots: WebUI-facing
exported text plus image, model, video, and decoded audio assets, never a
change under `webui/`, `reports/`, `memory/`, or `scratch/`. A serialized
payload diffs through its maintained reader and says so (`text_kind`); a
changed file with no diff says why (`text_diff_note`). Path-only relocations
with unchanged content are omitted. Build with `.\build_updates.bat OLD NEW`.

### Data

Files is one list shell over the Unity store, packed game files, loose decoded
files under `game/`, undecoded files under `raw/` (always a hex dump), and the
decoded datasets; SQL is a read-only console over either SQLite store. Store
sources and SQL need `serve.py`'s `/api/stores`; a static package or an older
server lists only the decoded datasets with an explanation. The record viewer
is taught no decoder-specific schema: it layers read order, framing, and
evidence chips onto the published structure by shape alone, labels `payload`
by its required `payloadKind`, and shows field names verbatim in every locale.
Dataset contents and publisher rules:
[`memory/webui/data_inspector.md`](../memory/webui/data_inspector.md).

## Verification

Build commands and their contracts live in
[`scripts/README.md`](../scripts/README.md); which workflow owns a changed
input is in [`memory/webui_recovery.md`](../memory/webui_recovery.md). The
shortest loop for frontend work is:

```bat
python -m scripts.game_data.extraction.verify_export_freshness
.\export.bat
python serve.py
```

After editing a frontend module, `node --check <file>` catches syntax errors.
The page smoke-test checklist is in
[`memory/webui_recovery.md`](../memory/webui_recovery.md). Its Story media step
uses the fixtures `test_sns_emojicomment`, `test_sns_sticker`, and
`sns_topic_map02_lv005_12002`.
