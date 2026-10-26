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
| `/api/stores*` | read-only Decoded-page store API ([`store_browser.py`](../scripts/webui/data_inspector/store_browser.py)) |

When present, root-level `endfield_paths.bat` supplies the current and previous
export mounts through `ENDFIELD_EXPORT_ROOT` and
`ENDFIELD_PREVIOUS_EXPORT_ROOT`. Explicit process environment values take
precedence; `WEBUI_PREVIOUS_EXPORT_ROOT` remains the server-specific override.

## Pages and routing

Nine main tabs, in navigation order. `data-view` is the tab token in `index.html`
and the value of `document.body.dataset.activeView`.

Chinese page headings use 人物汇总 (Characters), 文本表格 (Text),
视觉资产 (Assets), and 数据解码 (Data). Assets navigation is 资产;
Data navigation is 解码 / Decoded, with the English heading Data Decoding.

| Page | `data-view` | Scope | Behavior contract |
| --- | --- | --- | --- |
| Story | `story` | Reconstructed dialog, SNS, radio, cutscenes, media, and evidence-typed order | `app.js` |
| Gameplay | `gameplay` | Characters, equipment, enemies, combat stages, activities, items and their effects, recipes, machines, progression, skills, projectiles, and assets | `src/features/gameplay/{tabs,index,battle_stages,items}.js`, `src/features/gameplay/activities/index.js` |
| Map | `map` | Authored world-space evidence, encounters, patrols, NPCs and scene conditions with minimap, model, point, and water layers | `src/features/map_recovery/index.js` |
| Characters | `characters` | Identity groups, complete source appearances, verified Story links, related assets, and live overrides | `src/features/characters/index.js` |
| Text | `reference` | Searchable localized table/reference rows and configured achievement/activity targets and rewards | `src/features/reference/index.js` |
| Audio | `audio` | Wwise Events/media, authored contexts, decoded playback candidates, and recovery state | `src/features/audio/index.js` |
| Assets | `assets` | Exported images, models, video, and metadata | `assets.js` |
| Decoded | `data-inspector` | Files list over the export stores, loose and undecoded export files, and decoded datasets, plus a SQL console | `src/features/data_inspector/{stores,index}.js` |
| Updates | `updates` | Exported game-data changes between two complete versions | `src/features/updates/index.js` |

Gameplay's dataset bar contains Characters, Weapons, Essences, Equipment,
Items, Enemies, Combat stages, and Activities, in that order. Items combines
items and buildings, with recipes and machine configuration in their details.
Activities and Combat stages have their own catalog renderers within Gameplay.
The top-level Characters page owns identity and appearance recovery; Gameplay's
Characters tab owns playable-character stats, progression, and skills.

`recovery` is the tenth, debug-only tab revealed by `Show debug info`
(`src/features/recovery/index.js`, data from
`python -m scripts.webui.recovery.build_recovery`). It shows block volume and
each file type's L1-L4 recovery state, keeping recovery internals out of normal
navigation. The volume bar includes profiled, absent, metadata-unverified and
failed-read inventory, with distinct patterns and true shares in both byte and
file modes; family details list the same availability buckets. It shows
inventory composition, never the fraction recovered; states are scoped
declarations, not numeric progress; a missing or older payload shows an explicit
rebuild state. The optional authenticated JsonData registry checks the declared
L2 states by exact per-file path partition. Its missing state stays visible;
a present stale receipt or declaration mismatch stops publication.

Deep links are query parameters kept current with `history.replaceState`.
Selecting a Story conversation writes `story` and `lang` to the URL so refresh
restores it. Switching conversations clears the previous line/content focus;
reloading the same conversation preserves an explicit `line` or `cid` link.
`#<view>` also selects a tab. Unknown or retired hashes fall back to Story.
Gameplay accepts only current dataset routes; retired production/building/recipe
routes and selection parameter aliases are not supported.

| Parameter | Selects |
| --- | --- |
| `?ui=` / `?uiLang=` | interface locale |
| `?lang=` | data language |
| `?story=` / `?conv=` | Story conversation key |
| `?line=` / `?cid=` with `?story=` | Focus a rendered Story line or content ID and open containing disclosures; `cid` disambiguates repeated line IDs |
| `?activity=` | ActivityTable row ID in Gameplay’s Activities subpage (`?gameplayKind=activity#gameplay`); legacy `#activities` links normalize to this route and `activityTable` is ignored |
| `?asset=` | Assets entry by relative path |
| `?audio=` + `?audioKind=` | Audio record (`events` or a media shard) |
| `?gameplayKind=` + `?gameplay=` | Gameplay dataset (`character`, `weapon`, `gem`, `equipment`, `item`, `enemy`, `stage`, `activity`) and selected record. Items uses `items:<id>` or `machines:<id>` for a building without a published item; other entities use `<kind>:<id>`. |
| `?itemQ=`, repeated `?itemType=` / `?itemCategory=` / `?itemBuilding=` / `?itemTag=` / `?itemUpdate=`, `?itemSort=` | Items search, type, medal category, building category, relationship, version filters, sort. |
| `?inspectDataset=` + `?inspect=` | Decoded page, Files mode: the selected decoded record (dataset and record id) |
| `?dataMode=` + `?dataRoot=` + `?dataStore=` + `?dataGroup=` + `?dataName=` (+ `?dataQ=`, `?dataField=`, `?dataStatus=`, `?dataFolder=`, `?dataTag=`, `?dataSort=`) | Decoded page mode (`files`, `sql`), export (`previous`, omitted for current), selected sources (repeated `dataStore`: `unity`, `game-files`, `loose`, `undecoded`, `decoded`), selected groups (repeated `dataGroup=<source>:<group>`), the selected store row, search, and the repeated decoded filters and order; build with `WebUI.dataPageUrl` / `dataPageUrlForRel` |

Factory, World, Presentation, Progression, the standalone Combat & Projectiles
page, and the Mission Pipeline page are retired; their useful progression and
projectile information lives in Gameplay. Mission Pipeline recovery is a
standalone Python workflow; its retired frontend has been removed. Story still
reads the published Mission Pipeline index through `story_triggers.js`.

## Frontend map

Frontend consumers target current publications directly. Actor names are arrays;
Story options use explicit anchors; Data groups use source-qualified keys; Text
tables are complete records from the effective `game` source. Obsolete format
adapters and browser API shims do not belong in the frontend.

Load order, as `index.html` declares it:

| Files | Role |
| --- | --- |
| `index.html`, `style.css`, `themes.css`, `src/core/theme.js` | shell, shared layout and theme tokens; theme selection runs before paint |
| `src/core/sprites.js`, `sprite_worker.js` | registers the service worker that renders Sprite images; the first visit reloads once when it takes over |
| `src/core/{namespace,dom,loader,storage,text,locale,paths}.js` | globals, DOM helpers, fetch/caching, persistence, text, locale, paths |
| `src/ui/{media_player,splitter,filters,facets,sort,continuous_list,locate,pagination,update_badges}.js` | shared media player, resizable splitters, filters, sorting, virtual sidebar lists, detail pagers, and version-change comparisons |
| `src/ui/story_links.js` | Shared localized mission-to-Story navigation, loaded before Gameplay detail renderers |
| `app_labels.js`, `app_tree.js`, `src/features/story_triggers.js`, `app.js` | Story/Text labels, tree rendering, trigger evidence, Story page |
| `src/features/story/{branches.js,branches.css}` | Local option and SNS branch overviews; typed routes, manual annotations, and unresolved continuations |
| `assets.js` | Assets page |
| `src/features/characters/{appearances.js,index.js,style.css}` | Characters view, collapsible appearance records with source-checked Story navigation, and runtime overrides |
| `src/features/gameplay/detail.js` | shared entity, item and stage detail shell, metadata, sections and attribute cards |
| `src/features/gameplay/{items.js,items.css}` | Gameplay's item, recipe and machine catalogs using shared facets, sorting, continuous virtual lists, and Data file links |
| `src/features/gameplay/{labels.js,loadout.js,skill_refs.js,mechanics.js,index.js}` | Gameplay entity details, loadout, semantic summaries, authored skill references and item effects |
| `src/features/audio/{index.js,style.css}` | Audio evidence browser |
| `src/features/map_recovery/{index.js,encounters.js,style.css}` | Map view and selection-only authored encounter overlays |
| `src/features/next_views.js` | shared page-bootstrap wiring |
| `src/features/reference/{files,index}.js` | bounded file reads/cache and localized Text Tables browser |
| `src/features/gameplay/{battle_stages.js,battle_stages.css}` | Combat stage catalog |
| `src/features/gameplay/activities/{index.js,style.css}` | Gameplay Activities subpage, initialized before dataset routing |
| `src/features/gameplay/tabs.js` | shared Gameplay dataset routing, entry counts and lifecycle |
| `src/features/updates/index.js` | Updates page |
| `src/features/recovery/{index.js,style.css}` | debug-only Recovery progress page |
| `src/features/data_inspector/{index.js,stores.js,style.css}` | Decoded page: `stores.js` owns the mode switch, deep links, and the Files/SQL modes; `index.js` is the decoded-dataset source (catalog, matching, row markup, record viewer) |

Generated data belongs in `webui/data/`; user-managed inputs belong in
`webui/overrides/`. Do not hand-edit generated JSON.

Loading overlays name the current stage: download, reading, preparation or
display. Percentages describe downloaded bytes in that stage, using trustworthy
uncompressed response lengths; Audio weights parallel shards by bytes only
when every length is known. Unknown lengths, compressed responses and CPU work
show an indeterminate bar. No fixed stage weights estimate overall load time.
Stage changes paint before blocking work, and overlays close after the content
has had a chance to paint. Superseded requests cannot update the current load,
and an earlier fade cannot hide a restarted loader.

Gameplay orders its dataset tabs as characters, weapons, essences, equipment,
items, enemies, combat stages and activities; only the selected dataset's filters are shown.
The main Gameplay navigation tab opens Characters; explicit dataset links retain their target.
Opening the root URL leaves its address unchanged. Switching pages or Gameplay
datasets updates the route. Explicit links still select their target; local selections,
language choices, filters and loadout settings remain in their existing owners.
Restoring hidden Activities controls cannot rewrite the active page's URL.
Entering any Gameplay subpage loads the entity, item/building and combat-stage
indexes plus the activity count together, so every dataset tab shows its count
without first opening it, including direct entry into Activities.
Switching datasets reuses those indexes; actual language changes and page retries
refresh them together. A delayed Story language announcement for the already
requested language does not restart Gameplay. Concurrent Characters and
Activities activations share the current language request; Activities reuses
its initial ActivityTable payload when preparing the catalog. Unselected catalogs do not render or fetch details.
Items combines published items and buildings through exact building/item links.
Linked buildings render inside their item details; buildings without a published
item remain selectable Items entries. Building categories and power/recipe
relationships join item type, medal category and version filters in one sidebar.
The Gameplay items v1 index supplies item `buildingIds` and machine `items` for
this merge; no detail-shard download is needed to count or filter the catalog.
Types containing only one published item share the Other filter and list group;
details retain their authored type. The current publication supplies explicit
`catalogId` item references and `groupId` recipe references. No browser alias
map, recipe redirect or recipe-focus parameter is accepted. Item Story wiki
links reuse the shared Gameplay button.
Picture, business-card topic, snapshot sticker and avatar media follow their
authored table bindings. The Gameplay asset sidecar joins the Gameplay items
publication with Assets, independently of inventory icons; matching full asset
basenames prevents numbered stickers/topics from selecting neighbouring art.
All published items can show images and model candidates, including linked
buildings, even when they have no Gameplay use-effect entry.
Combat stages uses `src/features/gameplay/battle_stages.js` and its own
`lang/<LANG>/gameplay/battle_stages.json` publication (schemaVersion 3; entries
reference the shared `spawners` map through `battle.spawnerIds`) and the shared
Gameplay sidebar/filter-section and detail-header markup. `?gameplayKind=stage`
selects it; `battleStage`, `battleQ`, repeated `battleCategory`/`battleMode`/
`battleLevel`, and `battleSort` retain selection and filters. It groups authored
series, shows authored artwork, exact enemy variants and fixed reward icons,
and links to existing enemy/item catalogs. Enemy links retain the selected variant.
Data's last publication supplies stored spawn counts, wave/group/action offsets,
repeat/candidate/concurrency settings, birth Buffs and named script-Buff references.
Explicit dungeon-ID script branches or the stage's bound level script
distinguish stage-specific hosts from shared scene configuration. Counts and local offsets do not establish live population or
runtime wave order; unknown transitions remain visible. Raid-mode pairing requires
the explicit published mapping. Preview publications show their unavailable
mode mapping and last-publication boundary. One shared detail section combines
the description, objectives, special rules and map (`?map=`) and mission (`?story=`)
links. Stage background artwork appears only in the final shared Assets strip.
Paired-mode links name the destination mode and reuse shared Gameplay header
links and dataset routing. The generic configuration disclaimer is omitted;
preview and unavailable-mapping notices appear only when applicable.
Activities reuses this publication's direct activity/dungeon and character-trial
joins, identity-checked completion-condition references and season-configuration
destination links. Their section labels distinguish activity stages, completion
references and stored season configurations. Each stage row retains its own
map links: sceneId targets appear as combat maps and levelId targets as associated area maps;
levelId alone does not prove an entrance. Missing relationships produce no links, and season links
do not select the current live season/week.
Supply activities group each authored stage's text, submission requirements,
rewards and mission into one reading card. Submission chips link to Gameplay
Items and are excluded from reward totals. Stored mission references use the
shared reference-renderer link resolver and `src/ui/story_links.js` to open
missions present in Story's last localized publication; absent targets remain
plain text. Task-only additional stages are retained.
Each spawn configuration is one table with a row band per wave (numbered by position;
stored wave/group/config IDs are debug-only); spawns of one enemy variant,
level and Buff set in a group merge into one row with an avatar chip, summed
count and an offset range (per-spawn timings in the cell tooltip). Buffs
are small tags naming the first recovered effect; hover, focus or click opens
the full reference with the applier's blackboard values. Mode codes and source
dumps are debug-only. Buff semantics are not inferred from identifiers.
Kill-threshold, backup, alive-limit and repeatable chips carry tooltips and a
collapsible legend stating the stored field only; runtime effect is unconfirmed.
Entity and catalog sidebars reuse the same header renderer for entry counts and filter actions, without repeated dataset titles.
Items keeps Hide/Show filters and Reset filters
together in the sidebar header, available even when the filters are collapsed.
Gameplay details end with their published image assets. Gameplay item catalogs
include the icons displayed in their detail, deduplicated by asset path, in the
same preview gallery; Items retain their Gameplay images alongside those icons.
Character, Weapon, Essence and Equipment list rows omit their repeated kind badge.
The Items catalog automatically selects the first filtered
record when opened without an explicit ID. Formula item groups use centered flex
rows so operators align with item chips. Catalog and entity sections share heading
styles and omit horizontal separators. Building records retain their authored IDs and publication paths within Items.

Recipes have no standalone Gameplay tab. Current recipe links open
an output item's page, selecting the first published output for multi-output recipes.
Items load complete recipe shards for their source/use rows; inputs, outputs, cycle
rates, variants, formula items and stored conditions remain available there.
`itemRecipe` preserves the requested recipe for scrolling within the item detail.
Recipe publications and the shared crafting renderer remain in use.
Recipe rows omit the redundant View recipe link; item and building links remain.

Gameplay's entity, item and stage datasets share `src/features/gameplay/detail.js` for the image/title
shell, plain metadata, section markup, and attribute cards. Entity, catalog and
combat-stage renderers retain their data joins and interactions. Published images
supply the title thumbnail when present; missing images leave a text header.
All detail headers share their desktop/mobile padding, locate-button styling and
separate Story-link row; catalogs do not add their own header margins.
Character/weapon level attributes and Equipment attributes use the same
card renderer, while crafting input/output rows share the catalog recipe renderer.

Building details within Items retain the catalog's image and large title, with plain gray
metadata replacing the tag row. They share entity section headings and the Assets strip.
Shared asset strips keep bounded thumbnails and wrap images and model links within the detail width.
Gameplay asset images show their complete source filename below each thumbnail,
including its extension and object identity suffix. Long filenames wrap; image
preview captions use the same filename.
Thumbnail filenames are plain text; clicking the thumbnail opens the image preview.
Only Gameplay image popup captions link to the corresponding Assets entry and
close the popup on ordinary same-tab navigation.
Record items link to Audio event details through exact SpaceshipMusicTable row
keys and its musicEvent/musicEventSample fields. Full-track and sample links do
not imply that the current Audio publication has resolved playable media.
When Audio publishes decoded record-event candidates in
`lang/<LANG>/audio/record_media.json`, the same Assets section shows native audio
controls and complete filenames. Missing or empty media produces no empty player;
multiple candidates are labeled explicitly and are not a runtime branch selection.
Spaceship exhibit items link to exported models through
SpaceshipShowcaseItemTable.resPath and exact AssetMap prefab-container/Unity
type/PathID memberships. The Assets strip prefers a complete Animator model,
otherwise a highest-detail Mesh; missing exports produce no inferred model link.
An explicit manual model selection can fill an unresolved exhibit; it is labeled
as a temporary model with conditional evidence and cannot replace a direct
prefab model association.
Factory devices, logistics and decorations use table renderer references and
the effective FactoryUnitConfigAsset object index to show rendering Mesh PPtrs
in the same Assets strip. Collider and generic dropped-item models are excluded.
Composite devices follow resolved subAssets references to their part configs.
Segmented resource-prefix owner matches retain conditional evidence and display
as candidate models.
`gameplay_assets.json` image selections are manual display corrections, distinct
from the original ItemTable icon IDs.
Item images follow authored binary table fields first: `iconId` and exact
media-table references take precedence over filename conventions or manual image
selections. A declared icon with no matching exported asset leaves the portrait
empty. Quest ID/numbered-variant matching applies only without an authored icon;
reading artwork remains supplemental and cannot replace a declared icon.

Exact building/item pairs display their combined content in one item detail.
Building dimensions, power requirement and consumption appear in header metadata;
crafting sources reuse Equipment cards with input → output rows.
Catalog headers place IDs in the shared metadata line without a repeated kind subtitle.
The catalog evidence notice is omitted; stored configurations remain debug-only in this tab.
Equipment sidebar groups use authored suit IDs and localized names, retaining
collapsible individual rows and filtered piece counts. Entries without a suit
keep type grouping; filters still operate on individual pieces in the continuous virtual list.
Equipment rows also show their non-defense attribute names, using the same
localized stat labels as details. Equipment attributes is a multi-select facet
over those names, combined with type, rarity, search and suit grouping.
Each selected equipment attribute adds a sort category using displayAttrs'
base attrValue (level 1), defaulting to descending with the shared direction control.
Suit groups retain their members: groups appear by their first sorted member,
and members follow the attribute order within each group.
Equipment crafting lists every cost chain joined by EquipFormulaTable.level
to EquipFormulaChainTable, showing component and currency quantities with
item thumbnails from the last published Gameplay items icon lookup. It does not
expand component production ingredients, totals or time.
Items uses the complete Gameplay item catalog, adding the matching Gameplay
publication's AP recovery, use effects, action blackboards, chest rewards,
Story wiki links and optional asset gallery.
Item effects use the catalog's displayed data language; an unavailable Gameplay
publication shows a retry state without hiding the catalog or its relationships.
Rarity chips show only values present in the current dataset and subtype filters;
changing types clears rarity selections that no longer have entries.
Gameplay offers the shared sort dropdown for default relevance/type order, name
ascending/descending, rarity ascending/descending, type and ID. Explicit sorts
take precedence over search relevance; changing sort returns to the first page,
and reset restores default order while keeping the dataset tab.
Gameplay uses a shared dataset bar above both catalog panes. Audio and Data use
the same tab styling below their sidebar title. Reset keeps the selected
Gameplay dataset; recipe, ingredient, machine and reward links switch to their
target dataset. Browser history restores catalog selections and filters.
The item catalog merges type chips with identical localized labels and uses the
in-game encyclopedia groups for building chips. Available item and group icons
come from its compact lookup over existing exported media. Descriptions stay
expanded and use Story's rich-text/raw-tag display; building dimensions are
shown as depth × width × height, and empty relationship sections are hidden.
Machines label power consumption as electricity consumption. Each machine
recipe row shows ingredients → outputs with quantities and processing time,
and links its ingredient and output chips directly to their item pages.
Character breakthrough costs and potential values stay expanded. Character
avatar items use square head images; filled containers include their liquid/gas
icons, and medal tiers use their achievement artwork. Single-tier medals show
Level 1. Recipes producing the same complete output item set share one entry,
preserving each method's inputs, quantities and configured production time.
Recipe conditions and stored configuration use debug details in two columns on desktop.
Achievement medals share one entry per proved tier group, keeping every tier's description and
target; medal filters use the authored achievement categories. Medal list rows
and detail headers show every tier and plated icon on the left. Matching limited
items linked by `LTItemTable` also share an entry, combining their relationships
and retaining navigation/search through either original identifier. These catalogs use
the shared update badges and old/current source-field details. Gameplay list
rows reuse its optional asset-reference images as lazy thumbnails; characters
use horizontal face banners, following the selected Administrator gender.
Item pictures, card themes and stickers appear in the bottom Assets section,
using the same section heading and image/model strip as other Gameplay details.
Item image previews reuse the weapon/Essence Assets strip, including rounded borders and gray backgrounds.
Gameplay detail headers include Locate current file to open the selected record's list
page and scroll it into view while preserving the active filters.
Recipe methods and machine recipe rows show their required gas environment and
nominal input/output quantities per minute when a positive cycle time is known.
Rates preserve each method's stored groups and assume continuous operation.
The device list groups records by authored wiki category in wiki category order,
with uncategorized devices last and the chosen sort applied within each group.
All Gameplay lists show group headings: other catalogs use their first domain
filter (profession, weapon/equipment/enemy/item type, or crafting method).
Multi-method recipe records form a combined method group. Sorts operate within
groups; continuous virtual scrolling preserves one heading per group.
Group headings fold their records and retain their state while browsing;
Locate current file opens the selected record's group. Enemy configuration selectors and comparison rows show exact variant IDs and
per-variant update badges. Change details are separated by configuration, with
previous/current source values; Added means absent from the previous export.
Enemy update filters,
badges and detail evidence include every published variant ID in the group.
Gas requirements also accompany recipe references in item source/use panels.
The environment requirement appears first in reaction banners, before the
formula or recipe information.
Formula tags include Activity-only, derived from explicit craft-to-activity table
links. Combined recipes match when any method is activity-only; each method and
device recipe retains its own activity tag and ID.

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
webui/data/lang/<LANG>/characters/appearances/<identity>.json
webui/data/gameplay/items/manifest.json
webui/data/lang/<LANG>/gameplay/items/{index.json,items/*,recipes/*,machines/*}
webui/data/lang/<LANG>/gameplay/**
webui/data/lang/<LANG>/gameplay/projectile_audio.json
webui/data/lang/<LANG>/gameplay/{sound_effects,combat_relationships}.json
webui/data/lang/<LANG>/audio/{index,events,media}.json
webui/data/lang/<LANG>/audio/media.NNN.json
webui/data/lang/<LANG>/audio/{event_details,media_details}/**
webui/data/lang/<LANG>/audio/scene_backgrounds.json
webui/data/lang/<LANG>/audio/conv/{index,<key>}.json
webui/data/gameplay/projectiles.json
webui/data/gameplay/skill_refs/{index.json,<record-hash>.json}
webui/data/map_recovery/index.json
webui/data/map_recovery/maps/<levelId>.json
webui/data/map_recovery/encounters/{index,<levelId>,unplaced}.json
webui/data/map_recovery/render/*.{json,png}
webui/data/assets/{index,relations,gameplay_refs,story_media,table_owners,activity_media,videos}.json
webui/data/data_inspector/index.json
webui/data/data_inspector/datasets/<datasetId>/{index,records.*}.json
webui/data/updates/latest.json
webui/data/updates/{characters,story,map,gameplay}.json
webui/data/recovery/index.json
webui/data/story_order_ocr.json
webui/data/mission_pipeline/index.json
webui/data/mission_pipeline/story_triggers.json
```

Builders may add compact sidecars, but each page must tolerate an absent
optional sidecar and display an explicit degraded state when the omission
matters. Schema changes must be coordinated with their frontend consumer.

Characters verifies an appearance's source row, speaker and localized text
against the last Story publication before navigating. Story does not display
the module branch overview. Text guides retain exact table references and source
paths, keep condition codes in disclosures, and paginate rendered rows while
searching every loaded row. Targets, rewards and time ranges describe stored
configuration, not current availability or player progress.

### Ownership rules that are easy to get wrong

- `data/gameplay/projectiles.json` owns immutable projectile behavior. The
  language-specific `projectile_audio.json` and `sound_effects.json` are
  Audio-published sidecars that Gameplay reads: projectile audio loads with
  the base integration, and the large `sound_effects.json` loads in the
  background, filling projectile, skill and character/enemy sound sections
  when it arrives. A missing sound sidecar shows a warning, not an empty
  section. An event's optional `selectionTree` (authored Wwise structure:
  `play` roots, `layer`/`group`/`random`/`sequence`/`switch` containers,
  `sound` leaves with `mediaIds`) groups its candidates, and each audio player
  shows its file name: a Wwise layer container renders as one "played
  together" block, several Play actions of one Event render as an
  event-actions block (Wwise proves membership, not simultaneous onset), and
  each random/sequence/switch pool renders as one row with one column per
  alternative (same row: one is chosen; same column: played together; stacked
  groups sort larger first, single files last). Containers carry a yellow left banner, and the
  top container's kind sits in the event header. Branches with identical files
  render once, and events with the same file set collapse into one row naming
  the other events. An event reached only through a skill's BuffData chain
  names the buff holding its PlaySound action ("via buff"). Candidates
  outside the tree are listed separately; events without a tree keep the flat
  candidate list. Each event header has a Simulate button that resolves one
  trigger from the tree and plays it: layers and event actions all sound,
  random pools and multi-media sounds pick one, sequences advance per click,
  and switches take a random state (the runtime state is not published); the
  picked files are highlighted and a second click stops. Without a tree it
  plays one candidate at random and its tooltip says the structure is unknown.
  Every event is folded by default; its header (name, kind, Simulate) is the
  fold toggle, and its body is built on first unfold. On a skill card the
  exact-trigger sounds sit after the in-game description and before the
  upgrade cost, followed by the group's inferred skill-family sounds (owned
  only through the playable-skill ID prefix, badged inferred, minus files the
  exact group lists); they are rendered once and move with the level slider. A
  character's trailing
  related-sounds section omits files already shown on its skill cards (exact
  and inferred skill events and projectile audio) and files shown by an earlier group in
  that section, dropping events left with nothing new.
- `data/assets/gameplay_refs.json` is Gameplay-owned: the `asset-refs` stage
  joins the current Gameplay index to the Assets-owned broad index. The Assets
  builder never writes this consumer-specific sidecar.
- `data/lang/<LANG>/audio/conv/<key>.json` is Audio-owned and merged by Story
  at load; Story's own `conv/*.json` never carries voice.
- `data/assets/videos.json` and `data/assets/table_owners.json` are optional;
  the Assets page works without them.
- `data/assets/relations.json` holds the material/texture/model relations that
  only the detail panel and model viewer read; the page fetches it on first
  use, and a missing file leaves assets unrelated.
- `data/story_order_ocr.json` holds OCR order proposals only. It is generated
  evidence and never the active order.
- `data/mission_pipeline/story_triggers.json` is the Mission Pipeline's merged
  Story trigger lookup (coverage manifest, offline overlay, env_* manifest),
  read by Story in debug mode instead of the full index even though Mission
  Pipeline is not a page. Its absence is a degraded Story trigger state, not
  an error.
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

Range-slider thumbs share a circular theme-colored outline across pages,
including custom range controls and visible media-player seek handles.

Page headings share the 15px, 700-weight, 0.06em-spaced uppercase
style in `style.css`, including Activities, Audio and Gameplay's top catalog
heading. Their square accent marker shares the rule in `themes.css`.
The shared typography rule takes
precedence over feature-local heading defaults.


- Normal navigation exposes exactly the ten pages above.
- The top bar owns the data-language select (`#language`), the interface-locale
  switch (`#ui-language`), the colour-theme select (`#theme`), and the shared
  `Show debug info` toggle (`#show-debug`).
- Every list page with a detail pane shows Locate current file
  (`src/ui/locate.js`, `.locate-current-button`) at the detail header's top
  right; it expands the selected group and mounts/scrolls the selected virtual row.
- Themes (`themes.css`, applied before paint by `src/core/theme.js`, saved in
  `localStorage` under `webui.theme`) offer Endfield (light, default) and Talos
  Night (dark). Unsupported saved choices, including the retired Classic theme,
  fall back to Endfield. The HTML and base CSS also default to Endfield before
  JavaScript runs. Themes retune the `:root` tokens in `style.css`: palette,
  `--accent-text` (accent as text), `--on-accent`, status/syntax tones, and
  shape (`--radius-control/-chip/-tab`, `--shadow-sm/-md`). Feature CSS uses
  those tokens instead of literal colours, radii, and shadows; every page's
  reset button shares one rule.
- Debug state controls raw source blocks, recovery evidence, manual Story-order
  tools, and unresolved ownership details. Story issue and recovery-method
  filters remain visible in normal mode.
- Every list page shares one layout: a search box (`#*-q`), a collapsible
  filter panel (`#*-filter-panel`, `#*-filter-toggle`) of named filter
  sections, a reset button, shown/total counts, a resizable splitter, a
  continuous left list and a detail pane on the right. Sidebars have no page
  controls or item-count cap: all matches share one scroll range, while only
  the viewport and nearby rows are mounted. Shared `src/ui/continuous_list.js`
  measures variable row heights; row wrappers clip overflow without becoming
  scroll containers. Gameplay group headings retain collapse state
  and appear once per group. Assets, Audio and Story retain their existing
  virtual tree/row renderers; Map retains its hierarchical navigation.
  Filtering and sorting return to the start. Data Files discovers all source
  totals, then reads viewport blocks through the bounded store API with a
  limited metadata cache; dragging the scrollbar does not fetch intervening
  records. Very large scroll ranges are compressed to stay below browser
  height limits while rows retain their normal display height. Old sidebar page-size preferences are no longer read. Right-pane
  table rows, appearances and nested reference details retain their own pagers.
- Sorting places category and direction selects on one row: `Category` selects
  the comparison field; the direction select has no visible label and always
  allows ascending or descending order, including default ordering. Shared
  `src/ui/sort.js` controls preserve each page's sort values and handlers,
  and mount the Story-style labeled Search row above the category/direction row
  for every primary searchable sidebar. Characters and Gameplay combat stages
  also reuse these controls; Updates sorting stays in Basic filters.
  They combine direction-bearing options into one category and reverse unpaired
  comparators. Default order can also be reversed.
  Dynamic sidebars and interface-language changes reuse the same controls;
  resetting filters also resets the direction. Data's decoded-record browser
  uses these controls; SQL results retain the query's `ORDER BY`.
- All search boxes accept case-insensitive regular expressions. Queries are
  split on whitespace with OR semantics, so `^npc_`, `boss|elite`, and `map0[12]`
  are useful examples; malformed expressions are treated as literal text.
  Page searches include linked file paths and basenames, including audio files,
  nested media variants and same-content file aliases. URL-encoded references
  also match their decoded spelling. Lazy detail data publishes its file names
  in compact search projections, so opening a detail first is unnecessary.
  Story merges Audio's `audio/conv/index.json` `linkedFileSearch` map with its
  own `search.json` rows; Audio Events and Data catalogs carry an optional
  `linkedFileSearch` string. Filename matches keep all active facet filters.
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

- Mission summaries show notes; a separate block titled Mission Completion Rewards shows localized completion reward items with
  small item icons, quantities and links to Gameplay's Items catalog, including
  missions without notes. The Mission Summary title appears only when notes
  are present; completion rewards retain their own heading. The reward block is
  hidden when there are no resolved reward items.
  `mission/*.json` carries `extras.completionReward`, joined from the
  mission-level `MissionRuntimeAsset.rewardId` through `RewardTable` and
  `ItemTable`; quest-step rewards are excluded. Unavailable or empty reward
  lists show no block; random rewards are labeled alongside resolved items. Icons use
  the authored `ItemTable.iconId` and the optional Story media lookup.
  Mission Maps appear as small gray links in the metadata line below the right-pane title,
  from Map's published `data/map_recovery/index.json`
  (`maps[].missions`) and open `?map=<id>&mission=<mission>#map`.
  Story search includes completion reward names and item IDs for each mission's
  entries, without opening mission details first.
- Reset returns to Story sort and default filters while preserving expanded
  mission groups.
- Options sharing one response path render that dialogue once before the next
  prompt, including when the choice is inside another option branch.
- When every choice except one returns to the same menu, keep the advancing
  choice in that menu and show its response and later prompts below the menu.
  This layout requires explicit same-menu loops and one authored forward path.
  Subsequent shared dialogue and prompts keep the menu's layout level rather
  than inheriting the styling of an option column.
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

The project-authored Story entry `black_webui_secret_notice` uses the selected
data language for its title and three notice lines, independently of interface
locale. It remains explicitly marked as project content, not game evidence.

### Gameplay

Gameplay's entity and combined item/building sidebars use shared horizontal
filter dividers, capped at the filters' natural height and reserving 160px for
the entry list. Smaller filter panels scroll. Catalog renderers live under
`src/features/gameplay/`; there is no separate Gameplay items frontend page. Catalog
filters use shared section markup, collapse persistence and facet chip groups.
Dynamic facet headings carry the shared label marker so selected counts follow
the title, matching static filters. Enemies have no rarity filter or rarity
sort; their details reuse catalog section spacing and shared property cards.
Weapon header metadata omits maximum level, attack and model path because the
attribute and asset sections already display them. It also omits English name
and source; character and equipment header metadata omit source. Equipment
uses the same kind/ID-first metadata line as weapons and characters. All Gameplay
detail headers begin with `Type=… | ID=…` (localized type label) and use
`label=value` fields separated by ` | `; source fields are omitted. This covers
essences, enemies, items/buildings, combat stages and activities as well.
Enemy materials reuse the shared Gameplay asset strip: bordered gray image
cards with filenames, followed by model links in the same Materials section.
Enemy distribution labels resolve through `DistributionInfoTable.areaName`.
Map links require its exact `jumpId` join to `SystemJumpTable` with phase `Map`
and an explicit `phaseArgs.levelId`; general-area rows remain plain labels.
Energy Alluvium details link to maps using the published stages' exact
`WorldEnergyPointTable.levelId`, with repeated world-level targets merged.
Buff summaries distinguish complete stored framing from recovered effect behavior.
Known modifiers, duration and stacking fields can render alongside a pending
notice for unknown actions or unnamed event values; decoding a whole record
does not establish runtime activation or final effects.
Character metadata places ID immediately after kind, weapon type beside the
default weapon. Weapon English names come from
`WeaponBasicTable.engName`; they are not internal identifiers.

Gameplay equipment supplies may show linked trial equipment rewards with an
explicit unresolved per-box allocation notice; shared trial rewards must never
be presented as proven single-box contents.

Gameplay item/building details label item/building description sources only when
their text differs, and decorative text sources only when linked decorative
texts differ. Identical text is displayed once without a source label. Decorative
text and primary descriptions have no headings; decorative text appears last,
one font size smaller. Distinct text remains separate. Source presence
does not establish which description a game screen displays.
Gameplay item shards include `wikiDescriptions` (entry ID and localized text)
from exact wiki-to-item joins; item/building details render this explanation after
the decorative text using the shared rich-text renderer.
Gameplay items `labels` supplies localized building recipe/wiki headings from
`TextTable` keys and the catalog language's I18n table.
Recipe summaries include activity/gas requirements and original variants so item
recipe lists display each referenced craft's own conditions.
Currency purchase records show base prices, configured discounts and discounted prices, including an explicit no-discount label. Older publications missing discount fields show a refresh notice.
Item shop configurations are collapsed by default and show the deduplicated
count; items with zero configurations omit the section. Matching configurations merge goods/reward record identities while
retaining sources; shop identity, full rewards, prices, discounts, limits and
unlock/refresh conditions remain part of the comparison. Discounts are grouped
as variants within matching purchases, including currency-use records; every
distinct discounted price and all source links remain available.
Gameplay's base index carries `uiLabels` for matching equipment attributes,
set effects, enemy abilities/drops and weapon skill headings; these follow the
data language rather than the UI locale.
Weapon and equipment sidebar entries use two lines: the name, then metadata
with weapon effects or equipment attribute labels on the same truncated line.

Story item wiki entries and Gameplay's Items catalog have reciprocal links.
The item header's Story link requires a published wiki entry in the displayed
language and does not depend on Gameplay item effects.

Machine details display linked building items' decorative descriptions after
the machine description, using the catalog's displayed language and rich text.
Linked items and buildings share distinct descriptions, crafting/use connections,
building recipes, and Story links through their published identifier joins.
Exact one-to-one item/building pairs use the same combined detail layout from
either catalog, including both IDs, both sets of properties, and merged sources.
Combined details keep tags in one horizontally scrollable row, item/building
navigation in one reciprocal switch row, and both configuration disclosures
side by side.
Item crafting sources and recipe uses show the published ingredient/output
quantities inline, with recipe-detail links; configured processing time appears
only when the recipe provides it.
All recipe details keep unlock/operating conditions and stored configuration
side by side as initially collapsed disclosures, including recipe variants.
Building recipe lists group recipes by their stored gas-environment ID, showing
the environment once per group while preserving each recipe's activity tags,
ingredient/output quantities, and processing time.

Weapon list rows show the three localized skill effects in authored order.
Compact labels omit the middle-dot suffix and the first attribute's Chinese
increase suffix; hover shows the full skill name. The Weapons dataset has three
matching multi-select filter groups (Base attribute, Additional attribute,
Weapon effect) sharing those labels: OR within each group, AND across groups
and with weapon type, rarity and version changes. Switching datasets clears
them with the existing kind-switch reset.
Essences sits immediately after Weapons in the dataset bar. It lists authored
Energy Alluvium groups with area and the same three term-pool filters, pool
contents and compatible weapons. World-level variants and costs remain in the
published data but are omitted from the detail view. Weapon
details list compatible groups after Weapon effects, and group details link
back to compatible weapons; the compatibility rule and its evidence limit are in
[`memory/game_data/gameplay_semantics.md`](../memory/game_data/gameplay_semantics.md).
Essence list thumbnails reuse each group's authored icon through the optional
Gameplay asset sidecar; absent or broken images retain the text row.
Reciprocal compatible-weapon and farming-location links also show the target's
small icon inside the navigation button. The sidebar groups Essence rows by
localized region ordered by sortId and offers a region facet; unresolved regions
stay explicit, and no map coordinates are shown.

Gameplay owns character progression, equipment, enemies, skills, Buffs,
projectiles, and assets, and hosts the Gameplay-owned item,
recipe and machine catalogs. The `items` stage publishes the catalog alongside the other Gameplay stages: `export.bat gameplay` refreshes all Gameplay tabs from
the existing export. Character and enemy details use
a compact gray metadata line below the title and local section navigation.
Character Data / Loadout buttons follow the character name in the title row and wrap on narrow screens.
Weapon section headings share the character reading style, with spacing instead
of horizontal section dividers; weapon images use the same thumbnail strip and
zoom preview as character assets, retaining all linked models.
Weapon base attack uses plain effect text. Breakthrough and cumulative upgrade
costs keep currency beside other items, with currency links to the Items catalog.
Essence details use the same section and asset styles: Essence terms is one
three-column row of cards matching character potentials for base attributes,
bonuses and weapon effects, followed by
compatible weapons and image assets.
Weapon, Essence and Equipment image/model sections use the shared Assets heading.
Equipment uses Weapon's reading layout, section spacing and highlighted attribute
values. Manual model selections live in `overrides/gameplay_assets.json`; the
Gameplay asset-ref stage resolves exact exported base names and preserves their
manual-selection marker without claiming source ownership.
Equipment manufacturing keeps the formula link in one card and displays each
alternative separately with the shared Recipes input → output renderer,
hiding pack membership and undecoded unlock metadata.
Essence image previews group the same named icon's crop/resolution variants and
show the largest one; this display grouping does not equate their source assets.
Characters lead with parsed mechanisms,
then combat/base talents and growth. Enemies lead with authored combat traits;
configuration selectors update their attributes and attached effects together.
Mechanism summaries explain gated damage coefficients, projectile callbacks and
decoded attribute effects directly. Disabled actions are excluded; branch
contexts remain conditional. Values use only the owning skill's selected-level
parameters, never another skill's values or a runtime operand's stored fallback.
The in-game description is separate: its audit marks field-level support,
unverified effects and comparable numerical differences. Matching a damage type
does not verify an entire description; missing evidence does not prove a defect.
Raw actions, references and native formula expressions are debug-only. Unnamed
attributes and template fields remain expandable, and effect recovery status
stays visible. Damage and Poise calculations retain their individual native
gates and describe configuration inputs rather than final combat results. The
Loadout view computes final attributes only from a validated
`attributeCalculation` (`loadout.js`), including reviewed element-specific
damage-taken reduction factors. Weapon/set bonuses require complete,
identifier-matched SkillData reads, resolving the export's StringPool when present.
Weapon and equipment pickers show published
asset thumbnails and filter names, suit names, aliases and pinyin initials
(for example, 骑士精神 → qsjs). Weapon type and equipment slot restrictions
remain in force. Missing images leave the name selectable. Pinyin initials use
browser Chinese collation; polyphonic readings may need explicit record aliases.
The excluded essence modifiers are labelled 基质词条. Character metadata lists
主能力 followed by 副能力; separate character facets filter these authored
ability types alongside the element facet. Loadout equipment terms retain
主能力/副能力 when resolving to the selected character's concrete ability
(for example 副能力（敏捷）), without changing their calculation. The affinity-talent selector chooses the
unlocked attribute-node stage (or none), defaults to all nodes available at the
selected breakthrough, shows each node's affinity requirement as `floor(raw / 3)%`, and accumulates
its authored attribute modifiers with separate source labels. Evidence limits:
[`memory/webui/gameplay.md`](../memory/webui/gameplay.md) and
[`memory/game_data/gameplay_semantics.md`](../memory/game_data/gameplay_semantics.md).
Equipment main-ability terms use bold text with a background; secondary-ability terms use only the same background. Both retain their existing text colors, without underlines or borders. Character Loadout also highlights concrete equipment attributes matching the selected character's main or secondary ability, with textual labels; combined matches use the main-ability bold treatment. The matching changes with character selection and leaves calculation unchanged.

Item recipe cards select the exact source method from grouped `recipeVariants`,
including its machine, ingredients, outputs, time and environment. Shop cards
combine identical published display configurations with a matching-record count
and retain all goods IDs and source links. This is display grouping only.

Item storage limits appear in header metadata only for finite values greater than one. Equal storage/backpack limits share one label; different limits retain explicit storage/backpack labels. Building buffer limits remain separately labeled. Sentinel/default values are omitted without claiming unlimited storage. Raw item/building/recipe configuration remains available behind Show debug info; source identifiers, booleans and anonymous enums are not normal-view metadata.

Weapon and equipment records link both ways between Gameplay’s Items and their respective datasets using exact matching IDs in the displayed language. Header buttons appear only when the target exists in the current publication, share the Story Wiki button style, and sit beside it in one wrapping row using shared dataset routing.
Medal list, header and tier portraits use achievement level/plating artwork.
Their authored default inventory image remains in the Assets strip; missing
medal artwork does not fall back to that default portrait.

Quest items (authored ItemTable type 13) also include exported `reading_`/`read_` illustrations when the complete suffix matches their item ID or icon ID after removing the item/mission/quest prefix. This is a conditional display association, recorded as `quest-reading-name`, rather than proof of a runtime reading or mission join. Full basename matching rejects partial and numeric-prefix collisions. The largest original is preferred over cropped Sprite representations. Quest portraits prioritize the directly authored icon, including generic document icons. Reading artwork stays in the bottom Assets strip as supplemental conditional evidence. Filename matching and manual selections cannot replace an authored icon; a missing matching icon asset leaves the portrait empty.

#### Activities

Same-name official categories share a union filter without changing source IDs.
Stage and map navigation shares the related-link skin with weapon essence sources.
Activity overview reward previews show item names without quantities. Gameplay
item chips share an explicit quantity check: missing, invalid or unavailable
counts are omitted. Shared trial equipment lists do not show per-box quantities;
authored recipe, submission and fixed reward quantities remain visible.

Narrative activities expose the authored mission selection from an identity-matched
SystemJumpTable `detailJumpId` with phase `Mission` and a valid `autoSelectList`.
They reuse shared Story links and preserve list order; unpublished targets remain
plain IDs. Stage mission references remain visible even without rewards.

Supply stage details retain exact stage-linked submission items and quantities,
localized stage names, submission descriptions and notes in normal mode.
Submission quantities remain separate from reward totals.

Activities is a Gameplay subpage and builds nothing of its own. Its module lives in
`src/features/gameplay/activities/`; `gameplay/tabs.js` owns routing, entry,
language refresh and retry. Gameplay loads the ActivityTable row count from the
shared reference index on entry, so the Activities tab shows its total before
selection; activity details and supporting tables load on selection. Its
inputs, joins and evidence boundary are in
[`memory/webui/activities.md`](../memory/webui/activities.md). The default
filter is the authored ActivityTagTable name, followed by the technical type
and the schedule facet (Permanent activity for no configured end, Limited-time
activity for a configured end, unspecified when no ranges are stored).
Search covers IDs, localized text,
prerequisites, targets and rewards. OR applies within each facet group and AND
across groups; counts are dataset totals. Filter sections, panel visibility,
continuous virtual lists, sorting and splitters use the shared catalog UI. Desktop sidebar
width and filter height persist; a mobile horizontal divider resizes the list
above the details with touch or keyboard controls.

Opening time defaults to newest first, using the first authored time slot;
both directions leave undated
entries last. Name and authored display-order sorting remain available, and no
recommendation or schedule grouping overrides the chosen sort. Lists show
configured opening/closing times; lists, details, schedule facets and sorting
consistently use only the first authored time slot, verbatim, without assigning
a time zone. Full variants remain in the published source JSON.
List headings retain small outlined limited-time and permanent tags. The detail
header uses Gameplay's shared artwork/title/plain metadata shell, matching
Weapons and Essences, with Locate current file beside the title.
Reward summary, check-in/stage/milestone rewards, schedules, artwork and guide
headings use the shared Gameplay section-title typography and theme color.
Schedules and activity prerequisites have no enclosing card. Linked reward
cards keep their content and descriptive day/stage names, with one outer reward
section heading and no repeated headings inside the cards.
Same-name source activities remain separate records with their own conditions
and rewards.
Activity descriptions and compact guides normalize stored size/color tags to
ordinary bold emphasis, using WebUI typography rather than the game's font
sizes and colors. Full debug reference text retains the source markup and
shared raw-tag mode. Text fields use the shared safe rich-text renderer.

Activity lists retain their original rounded cards, title, official categories,
configured time and yellow selection rail. Authored tabImg occupies the right
44% of each card at full card height, covering its area; missing artwork leaves
a text-only card. Source IDs stay in tooltips and debug mode; completion marks are
not synthesized without player-progress data. Update
badges and field comparisons appear only in the right detail pane, whose
header precedes the shared update panel as in Gameplay: title, concrete
changes, then source identity and configured content.

The detail pane uses Gameplay’s header and body spacing with a centered empty
state and no introductory configuration-boundary paragraph or image background. The localized root Desc is
rendered below the title and official category tags. The redundant Activity
configuration section is omitted in normal mode. Normal mode keeps schedules, prerequisites,
targets and rewards while omitting duplicate Desc/time fields, guide boilerplate,
technical codes and duplicate raw text/fields when a maintained guide exists.
Machine-facing activity/reward/time/mission/jump keys, reference provenance,
display-order settings and unfilled runtime text placeholders are debug-only.
Reward quantities remain visible even when an item name is unavailable.
Every activity detail places Reward summary after prerequisites and before
stage/check-in/milestone rewards, summing published fixed
rewards into wrapping item tags using Gameplay's shared item-chip styling,
with an optional icon, item name and quantity. It sums fixed reward entries by
item ID from exact linked check-in/stage/task/milestone rows.
Each reward tag links by exact item ID to Gameplay's Items catalog; maintained
ItemTable field links in activity guides and Text use the same destination.
The ActivityTable overview is used only when no quantified detail is published
and is explicitly labelled as a preview, never added to the detail total.
An absent reward publication produces a visible unavailable note.
Source identity and full fields are available with Show debug info.
The final Assets section is visible in normal mode and reuses Gameplay's shared
asset strip, previews and asset-page links. It collects exact published activity
and supporting reward images, including authored tabImg and bgImg. Each authored
image token displays only its highest pixel-area representation; source alternatives
remain in the publication. Exact referenced
records, including reward items, receive one matching icon from
`data/assets/activity_media.json` before their field value, with a source-field
tooltip and shared image preview; Sprite crops are preferred over duplicate
Texture2D representations. Missing media publication is reported inline.
Check-in days and activity-keyed stage, task and milestone guides expand in
the detail with their own reward quantities and item icons. Exact references
open the owning row in Text. Within the Gameplay Activities subpage, the catalog always uses ActivityTable; supporting tables remain linked detail sources. `activity`, `activityQ`,
`activitySort` and repeated `activityType`, `activityTag`, `activitySchedule`
preserve selections and filters. Missing data and load failures remain visible;
UI locale and data language follow the shared controls.

### Map

The floating control panel keeps its dragged position, resized dimensions,
collapsed state and scroll position when switching maps or changing filters.

Map plots authored Unity X/Z and draws a background only when the image and its
world bounds share an explicit transform. Generated contract:

- `data/map_recovery/index.json` lists maps, their exact `regionKey`, the
  default map, and compact counts; `maps/<levelId>.json` owns markers, quest
  points, facets, mission/file evidence, minimap metadata, `mapMark`
  annotations with `mapMarkCoverage`, and one render manifest; `render/` owns
  generated minimap composites, Terrain byte previews, elevation, surface,
  point, height-mask, and water PNGs plus manifests.
- Deep links: `?map=<map or variant id>` opens that map once; an optional
  `?mission=<id>` selects that mission when the map's facets list it. Mission
  files link back to Story conversations.
- Declared DungeonTable.sceneId maps remain published without registry or Story
  points, with separate scene payloads and streaming sources. Their empty point
  arrays claim no recovered positions; stages sharing an exact scene ID can
  link to the same map.
  Distinct standalone dungeon scene IDs retain separate regions even when LevelConfig
  points to shared Streaming art; preview reuse never merges task/marker spaces.
- Shared-scene identity comes only from the directly addressed
  `LevelConfig/<levelId>.json` streaming path. Streaming-instance sidecars use
  schema 2 with one `meshes` array per entity base. Newly built Mesh rows record
  `identityEvidence`: `exact_level_hlod_key` or `name_family_candidate`.
  The latter is preview geometry with an exact instance matrix but unproved
  prefab-to-Mesh ownership; Map labels it as such. Older sidecars without the
  field need rebuilding; the frontend reads the current `surfaceEvidence`
  directly and does not synthesize legacy grades.
- Every point layer owns its height mask (`pointCloudOverlay.heightMask`), and
  region bounds are derived in the browser from loaded background rectangles.
- Registry markers may carry `interactive` template/name evidence and
  structural presentation categories. `interactiveCatalog` owns shared source
  links and availability diagnostics; subtype facets own localized `labels`
  and `icon` keys. Device glyphs match the subtype legend, and the inspector
  distinguishes official facility names from identifier-based categories.
  The Facilities preset selects devices and travel objects. Search narrows
  the legend only; selecting a subtype enables its parent without revealing
  the other subtypes. Partially selected parents have a distinct appearance;
  clicking one selects the whole group. Counts show plotted/total markers.
  The floor-hidden summary counts only otherwise eligible points, and its
  action enables their floors without changing type or mission selections.
  Manual type selection clears exclusive mission/Story/map-mark filters;
  map-floor controls remain independent. Registry previews follow the exact
  selected entity identity, including when two points share the same file.
- A reviewed `authoredWaterSurfaces` row in a render manifest is a world-space
  LevelData footprint whose stored hash resolves to an exact Mesh asset and
  whose conditional native setup/initial-height path passes the current-build
  gate. The water toggle draws that polygon separately from `waterOverlay`, the
  authored minimap color mask. The polygon records authored placement. A
  selected `runtimeObservation` appears only after the saved live capture,
  exact native inputs, and authored source all validate; it reports a returned
  surface Mono and Mesh delivery to `UpdataMesh` at the requested initial
  position. The tooltip distinguishes the saved v1 pointer-based ID check,
  a later managed-string ID match, a mesh-only capture with no position
  samples, and any separately validated Setup-return or setter-return
  Transform positions. A requested position is not an observed Transform
  position. None of these fields establishes final water height or renderer
  visibility. A failed source or native gate publishes no polygon.
- Proximity is never upgraded into ownership; weak spatial or mission context
  stays separate from identity links, and non-Story evidence files stay behind
  `Show debug info`.

Marker eligibility and render-layer grades:
[`memory/webui/map.md`](../memory/webui/map.md) and
[`memory/game_data/story_carriers.md`](../memory/game_data/story_carriers.md).

### Characters

The catalog discovers speakers directly from exported dialog, radio, ambient
talk and mail Tables, with optional explicit NPC proxy name references. It
requires no Story page build. Labels without speaker ids appear as unresolved
Story speaker candidates, stay separate from automatic same-name groups, and
show bounded localized source-line samples and occurrence counts in evidence.
Question-mark labels with a single named annotation (`？？？{亨德森}`) use the
annotated name and join its plain-name candidate, retaining the original label
in evidence. Explicit `A&B{异口同声}` labels contribute separate joint-speaker
evidence to each participant. A unique standalone authored speaker name may
select an existing identity; ambiguous or missing matches stay candidates.
This name-based association remains unresolved evidence and preserves the
original label and line. Other compound annotations remain separate.

Merge and name overrides are live inputs written through `serve.py` and need no
rebuild. The optional `data/updates/characters.json` adds version-change badges
and filters plus old/current detail comparisons; it never changes grouping,
naming, evidence, or overrides.
Grouping, search text and evidence counts are cached until catalog or override
inputs change. Searching preserves the selected detail and expanded evidence
when that identity still matches, without re-rendering its detail on each input.

### Text

Text keeps raw JSON access beside the rendered view, so unsupported fields
remain inspectable. Maintained `fields` link only to a resolved row in a table
present in the Text index; unresolved references are never linked.
Raw files use a streaming preview capped at 256 KiB, with a full JSON download
link; partial previews retain source formatting and state the limit. Complete
small files retain localized formatting when it fits the preview budget.
Additional same-content files load on demand, and switching tables cancels
obsolete detail downloads. Rendered shards above 32 MiB show an explicit size
limit; table caches retain at most eight entries within a 24 MiB source-byte
budget. Text renders at most 100 rows per page and 100 text entries per row;
both pagers retain access to all loaded entries, and search covers them all.

### Audio

The existing runtime panel can show bounded full external-source paths and
cookies from a verified complete capture. These are managed request arguments;
the summary keeps them unbound when the decoded index lacks an original full
VFS source path for exact comparison. It does not infer media ownership from a
short dialog path, basename, cookie or timing.

A separate anonymous-source capture panel renders bounded source-pair counts,
flag-state observations, and audited synchronous consumer/LockDataPtr
relations from `runtimeObservations.nativeSourceCaptures`. Its publication
rechecks the exact saved trace, diagnostics, profile, and selected native
inputs. Missing or changed evidence produces a visible degraded state. These
captures can carry `sourceSummary.sourceBridgeRelations`, whose bounded
representatives show selected native text, cloned source, constructed owner,
and consumer/Lock relations within the audited same-thread interval. Optional
`sourceSummary.ownerCarrierRelations` shows entry-only carrier/decoder-owner
snapshot matches and fixed source fields at the reviewed control callsite.
It does not interpret source pointers as text/media or establish an internal
branch or continuity from an earlier selector. All representatives share the
existing global sample budget. Text
renders as plain evidence, without file, audio, Event or media links. These
rows stay outside Event and media details; they establish neither an
asynchronous managed-path owner nor pointer lifetime, file selection, codec
use, or audibility.

The optional `nativeEntryObservations` detail admits one complete native
source/owner session independently of paired recordings. Publication replays
the selected recipe, staged identity, writer and window receipts before showing
per-hook counts, bounded terminated native text and local source storage fields.
Missing/mismatched inputs withhold all rows. Text stays grouped by hook with no
inferred chain or Event/media links; zero carrier entries mean no snapshot in
that window, not an absent playback path. Interrupted sessions stay diagnostic.
The optional child `providerEntryObservations` uses
`endfield.audio-provider-entry-observations.v1`. Its separate selected dispatch
gate admits per-hook caller roles, local address-point comparisons and input
text states. It distinguishes source-based preparation from decoder preparation
without joining entries. A failed child gate shows its bounded reason and
preserves admitted base entries. Neither an open-dispatch entry nor terminated
input text establishes completed storage, file opening, decoding or audibility.
The `ioEntryObservations` child uses
`endfield.audio-source-io-entry-observations.v1` and independent retention,
storage and package gates. It shows retained provider/device states, default
package I/O address-point matches, independently authenticated hash/lookup
inputs and bounded table-count cohorts. Full-width package keys are decimal
strings, never JavaScript numbers. Complete source-I/O recording admission
now supplies these observations. The expanded recipe's optional
`packageCompletionObservations` child uses
`endfield.audio-package-completion-entry-observations.v2`; its separate result
gate requires authenticated caller/address point and local request/back-pointer
and result equality before displaying bounded status-success descriptor
samples. A complete expanded recording supplies these fields. The v2 child
compares the gated external path key low word and modulo-width byte offset;
full-width computed keys remain decimal strings. It groups repeated descriptor
samples across the whole window and prioritizes text before applying its bound.
No sample creates an
Event/media link, selected-row claim, backing-file identity or decoded result.
The independently gated optional `packageReadObservations` child uses
`endfield.audio-package-read-entry-observations.v2`. It shows bounded per-hook
counts, platform error and transfer-size comparisons, and local pre-transform
descriptor/cookie samples. The first batch record does not represent the whole
batch; the guarded buffer word does not represent decoded PCM. Full-width
lengths and positions are decimal strings, and this child requires its own
expanded recording, now admitted. Descriptor geometry cohorts aggregate the
whole window before bounding the display; transform-range unions show metadata
coverage, with gaps preserved, rather than complete retained buffer contents.
Optional `observedCoverage` reports all checked transform entries by encryption
flag, relative offset alignment/origin and descriptor-range class. The display
labels this as observed-window diversity, not installed-corpus coverage. Optional
`sampleSelection` and `descriptorCohortSelection` describe deterministic
stratified representatives and disclose omitted strata; aggregate counters are
computed before display limits. Geometry/handle strata are grouping keys, not
allocation or lifetime identities.
Optional `encodedWordWitness` uses
`endfield.audio-package-read-word-witness.v1` for comparisons against a supplied
bounded package candidate index. It shows matched/sample-word and distinct-byte
counts; candidate package paths do not become live file identities or media links.
Representative buffer words are behind a nested disclosure. The optional
aligned transform gate controls calculated clear words and anonymous callback
identities independently of read admission. No cross-entry ownership or
Event/media links are added.
The disclosure also labels the static embedded-transfer/back-pointer and
conditional primary-provider and separate queued-receiver interface proof. Their anonymous state changes and
wakeups do not identify the live receiver or game codec. A focused native-entry
refresh may replace only this independent top-level child in a current
schema/language index; Event/media shards and other projections remain as
published. Concurrent index replacement withholds that refresh.
The independent `managedPostObservations` child uses
`endfield.audio-managed-post-observations.v1` and displays bounded local
request/result pairs: Event ID, full-width audio object ID as a decimal string,
external-path projection, returned playing ID and raw callback-type argument.
These pairs create no asynchronous native ownership or media links. Missing,
lossy and truncated projections stay distinct from complete ASCII projections.
The new transfer recipe may also retain original external cookie and raw Beyond
codec arguments in the external-post result; older recipes leave those fields
absent. The raw enum argument is not a game codec instance.
Optional `offlineDecodeObservations` uses
`endfield.audio-package-offline-decode-observations.v1`. It displays prior
offline PCM comparisons only while the candidate, retained selected bytes and
explicit decoded-file identity still match. Failure withholds this child,
preserving admitted native read facts. Channels/rate/duration and PCM equality
describe offline decoder output; no Event/media player link or game-side codec
claim is introduced.
For a separately admitted transfer recording, `transferReceiverObservations`
uses `endfield.audio-transfer-receiver-entry-observations.v1`. It displays local
user-data/block and receiver/node comparisons under mandatory read/transform
gates. Address points select reviewed interfaces only. The dispatcher recycles
its block before invoking receivers, so later handler carrier values remain
anonymous and cannot close an original-transfer or lifetime join. A recording
without these fields displays the gap instead of inheriting newer observations.
Optional receiver `sampleSelection` separates hook, interface family and local
check outcome, so repeated transforms cannot consume every displayed slot when
other strata fit the limit. Failed local checks retain diagnostic samples only.
Prior recipe versions retain their exact declarations. Counts remain per hook;
computed package keys do not annotate Event/media rows or prove selected bytes.

The optional top-level `staticProviderPreparation` projection uses
`endfield.audio-static-provider-preparation.v1` and `evidenceKind=static`.
Its independent explicit selected-native gate publishes allowlisted direct or
conditional claims only on `status=validated`; other statuses show unavailable
evidence. The Runtime panel keeps it separate from captured observations and
renders no Event/media/audio links. It describes decoder/owner/source reads
and temporary provider descriptors. Optional `providerStorageStatus=validated`
admits two additional conditional claims about initialized dispatch, output
interfaces and owned UTF-16 storage; the frontend requires that separate gate
and the exact allowlisted tier. A failed storage gate preserves preparation
and shows its bounded unavailable reason. File, codec and playback identity
remain unresolved.

Optional top-level `packageCatalog` uses `endfield.audio-package-catalog.v1`.
Its optional language-table projection retains package-local stored IDs and
UTF-16LE labels. Bounded row/label previews mark truncation, and unknown IDs stay
unresolved; labels do not establish a clip's spoken language or live selection.
The published catalog keeps this static installed-package inventory separate
from capture observations; the page no longer renders it. A complete current VFS/AKPK gate supplies package and
typed-entry counts, bounded package rows, repeated typed keys and full-key
collisions after low-word truncation. Bank-header identity counts cover only
the stored BKHD prefix joined to each full bank key; version counts retain the
stored value and do not claim whole-bank parsing. Full keys and lengths stay decimal
strings. Missing packages remain excluded; duplicates never select a package,
Event, decoded media or runtime handle. A failed focused refresh publishes an
unavailable child without stale counts. The single Audio command's
`--package-catalog-only` mode atomically replaces only this child in a current
schema/language index and rejects concurrent replacement. A regular semantic
rebuild revalidates a previously selected inventory through the same raw gate;
it retains only the expected roster identity, never copies prior package rows.
A missing prior selection skips the scan, and a changed roster becomes unavailable.

The independent `--runtime-source-only` refresh replaces only native source/owner
fields inside `runtimeObservations`. It requires the same published bundle path
and digest, current selected native inputs and an unchanged index at replacement.
Other runtime fields and Event/media annotations retain their existing evidence;
a failed source gate replaces its old claims with an explicit degraded state.

Selector branches join direct Sound children to media only within the same
full package path and bank ID. Older basename-only media evidence resolves
only when surrounding Event evidence names one complete package scope.
Missing or ambiguous scope retains unresolved media candidate IDs and a visible
package-identity note; it never becomes a direct media link.

Audio keeps four layers separate and claims only the available one: authored
Event or media identity; Wwise graph relation and possible media leaves;
authored consumer/trigger context; observed runtime execution. Status fields
render verbatim in details, search, and filters; the token vocabulary is listed
in the header comment of `src/features/audio/index.js`. Notes are written only
on an explicit `Save note`. Missing or mismatched native inputs remove only
build-locked callsites, mappings, and addresses, with the unavailable state
shown. The effect gate distinguishes named authored settings from anonymous
native input reads. An expandable `structuralOnly` table shows read offset,
width, kind and raw bytes; float32 views are representations with unresolved
control meaning. Direct-effect rows stay in lazy media details, with every
other panel-only media field (Event/trigger context, Wwise media graph,
post-process, content hash); list shards keep only what list, search, sort and
facets read. Bus parameters
remain in the unique shared catalog. What each state refuses to claim is in
[`memory/webui/audio.md`](../memory/webui/audio.md); the Wwise chain is in
[`memory/game_data/audio_overview.md`](../memory/game_data/audio_overview.md).

### Assets

- Recovered collision OBJs have a separate `Collision` source and `cl`
  metadata (triangle/convex kind, full serialized identity, cooked-buffer hash
  and geometry counts). The `Collision` tag starts off and reset turns it off.
  Collision rows never share a render-model group or inherit name-based
  material/table ownership. Their previews use mesh local coordinates and
  original cooked winding; the preview applies no scene transform.
  OBJ files live under `data/assets/collision/`, with the source root recorded
  in the index so local serving and the resources package use the same files.
  An unavailable current corpus publishes no collision rows and records its
  diagnostic for the tag tooltip.
  Optional `cl.runtime` v1 evidence joins admitted getter/cache observations by
  full CAB/PathID, physical source/offset and raw/cooked hashes. Details distinguish
  decoded geometry, observed query geometry, uniquely matched movement returns,
  accepted filter candidates, complete arrays versus captured prefixes, and
  conditional surface comparisons. Initial-overlap/nonpositive sweep points are
  excluded from surface comparisons. Solver contacts remain unproved. A missing
  observation does not mean unused. Invalid runtime inputs clear only runtime
  claims, with a diagnostic in `collision.runtime`; stored previews remain.
  Enable the Collision tag and search `observed` / `已观察查询`,
  `movement` / `移动结果`, or `captured` / `捕获前缀` to find
  sampled evidence without promoting filter candidates to movement results.
  Optional `cl.authored` v1 metadata records freshly revalidated stored
  MeshCollider/prefab owners, joined by full physical identity and raw/cooked
  hashes. Details show prefab paths, reciprocal root-to-collider hierarchies
  and authored enabled/active flags. These do not prove live instances,
  activation or world placement, and previews retain mesh local coordinates.
  Search `authored` / `存储归属` with Collision enabled to find these owners.
  Invalid scene receipts clear only owner claims and expose their diagnostic.
  Optional `cl.models` v1 metadata links exact collider owners to native-gated
  authored Model source records through the manifest path, logical Bundle and
  declared prefab root. Details show source records and stored transform axes;
  grid transforms and final world placement remain unproved. These values never
  alter the mesh preview. Search `configured` / `定义场景` to find them.
  Links to Data's raw source rows require authenticated files in the selected
  export root. Invalid Model evidence clears only these source labels.
  Optional `cl.prefabs` v2 metadata links generated assemblies through the
  `CollisionPrefab` source root. Details offer assembly preview, single-mesh
  reset and OBJ downloads. Assemblies group by physical prefab root and apply
  each selected MeshCollider and separately admitted BoxCollider's stored root/descendant transforms, retaining
  disabled/inactive definitions and counting selected unrecovered siblings.
  Mesh and box counts stay separate; box details retain full size, local center
  and trigger flags. Search `BoxCollider` / `存储盒形` to find boxes. Other
  primitive/custom and unselected colliders remain outside coverage; runtime
  grid/parent matrices and world placement are not applied. Search `assembly` /
  `组合预览` to find these variants. Invalid assemblies clear only their links.
  Optional `cl.renderers` v3 records selected MeshFilter/MeshRenderer components
  in the same physical prefab roots. Details show stored component hierarchies,
  enabled flags, Mesh reference status and ordered material slots; expandable
  records expose exact decimal pointers and distinguish unresolved/excluded
  targets. Search `MeshRenderer` / `渲染组件` or `material slots` / `材质槽` with
  Collision enabled. Selected target identity does not prove decoded render
  geometry, material appearance, live drawing or world placement; other Renderer
  classes remain outside coverage. Invalid renderer evidence clears only these
  labels and retains the other collision projections.
  Independently admitted resource scopes add exact Mesh/material target names,
  stored Material JSON downloads and neutral render previews through
  `StoredRender` under `data/assets/stored_render/`. Stored LOD buttons use actual
  LODGroup memberships; assembly coordinates include root/descendant stored TRS.
  UV sets remain distinct in stored evidence; OBJ previews use UV0. Runtime
  shader/material appearance, LOD selection, vertex overrides, animation and
  world placement remain unproved. Resource failures restore component-only
  labels and clear only render artifact links/source root. Original collision
  files and previews remain available.
  Stored-render v2 and Material-document v2 also expose exact-source Texture2D
  PNG thumbnails and full image links under each material's stored texture
  details. UV set, tiling/offset, dimensions, block format, stored mip count and
  colour-space enum are displayed; full sampler fields remain in the JSON.
  Images retain decoded top-mip channels with a vertical export-coordinate flip;
  no gamma conversion, normal reconstruction or shader appearance is implied.
  Texture decoding failures preserve neutral render previews and stored refs.
  Stored Material links also offer lazy Shader details through the independent
  `data/assets/shader_analysis/index.json` sidecar (v3). Bindings require the
  published Material artifact hash; source publication requires exact physical
  Shader identity and raw hash. Details expose stored keywords, passes,
  conditional keyword-superset program counts and an analysis JSON download.
  Missing or stale bindings remain unavailable. These candidates allow extra
  engine keywords and do not establish runtime variant/pass/resource selection;
  neutral previews remain unchanged.
  Shader details separate explicit numeric Material values from unoverridden
  Shader declarations. Per-pass conditional parameter tables show named resource
  presence and constant-buffer offset alternatives; these are table declarations,
  not instruction-use or live-upload claims.
  A separate compiled-input section counts conditional VS/PS instruction
  references, checked register joins, named field reads and offset alternatives.
  Dynamic and anonymous reads remain visible, and malformed instruction rows
  fail closed. These static reads do not establish runtime program execution,
  uploads, sampler state or source Material ownership.
  Recovered renderer/material inspectors use the full width below the preview.
  Stored texture details offer RGB/R/G/B/A inspection on the exact referring
  renderer's material slot. This checks the Mesh OBJ and PNG artifact hashes,
  uses the declared UV0 or an independently admitted UV1 projection plus stored scale/offset and wrap modes, and shows decoded
  top-mip channels without lighting, tint, colour conversion or transparency.
  Other slots remain neutral. Unsupported UV sets, sampler enums, non-drawable
  slots, WebGL limits or artifact mismatches show scoped failure diagnostics.
  Trilinear storage is inspected as bilinear at mip zero; runtime samplers,
  original mip selection, multi-layer arithmetic and game shading remain open.
  UV1 copies live under `data/assets/mesh_uv/`, reached through a lazy v2 sidecar
  and the `StoredUV` source label. Publication first reproduces the original UV0
  OBJ byte-for-byte from fresh admitted Mesh buffers, then changes only `vt`
  coordinates. Bindings require the original Mesh artifact/body hashes and
  stored-render publication root, including when UV0 stays unchanged; this does not
  rewrite or renew the existing asset index or imply live UV selection.
  Preview evidence and diagnostic notes appear above the image/model, so the
  inspection mode and its limits remain visible when the preview is tall.

- OBJ rows carry `nd` when no valid face can emit a triangle. The
  `Empty mesh / no drawable faces` tag starts off and reset turns it off;
  enabling it includes those rows alongside ordinary assets. Empty variants
  form separate groups from drawable variants. Their details and preview
  explain the missing surface and retain identity and download links. Point-only
  previews report their source vertex count even though no triangle is drawn.
  Empty-model messages use the page background and hide rendering controls.

- Assets details use plain preview and information columns without enclosing
  card borders or backgrounds, stacking into one column on narrow screens.
  Metadata uses label/value rows; related files and model statistics use simple
  dividers, with no rounded preview frame or pill-shaped detail controls.

- OBJ and FBX previews share background presets, a custom background picker,
  and a model color picker. Colors apply to both WebGL and software previews.
  Initial framing fits the bounds' enclosing sphere to the narrower viewport
  dimension so bulky models stay inside the canvas when rotated. Zoom/pan
  remain relative to that fit. Small flat meshes normalize using their actual
  nonzero extent; FBX fitting excludes initially hidden LODs and proxies.
  Model only switches WebGL to opaque geometry in the chosen model color,
  disabling material textures, tint, emission, blending and alpha clipping.
  The software preview already uses untextured geometry. The switch stays
  selected when changing models within the page; it does not deform VAT meshes.
  Non-additive transparent surfaces without depth writes sort their triangles
  back to front as the camera rotates, within each material's queue-ordered
  draw range. Intersecting transparency and game effect shaders remain approximate.

- Assets lists images, video, OBJ, and FBX, not exported JSON: every such
  document is a Decoded-page store row, and a material links to its Decoded-page
  document. The optional `Table owner` fact requires an exact whole-stem match
  in an asset-bearing field.
- Assets chip counts are totals over grouped asset entries. Type, category,
  source, and search can narrow the result to zero; chip tooltips and the
  empty-list message explain this and point to clearing search or resetting.
  The filter panel scrolls within half the viewport height so expanding the
  category catalog keeps the results visible.
- An Animator FBX is grouped by the scene it belongs to, not its file name:
  the index records its FBX root as `fr` when that differs from the file
  stem, so generic cutscene objects (`Actor`, `offset`, `GameObject`) sit
  under their timeline, with `<name>_Actor`/`<name>_Effect` roots merged.
- Sprite images are crop documents over their textures, still linked as
  `.../game/Unity/Sprite/<name>.png`; `serve.py` answers with the crop
  document and `sprite_worker.js` renders it pixel-identical to AnimeStudio.
  Without the worker (no secure context) Sprites do not display.
- Animator FBX are rows in `Unity.sqlite`, still linked as
  `.../game/Unity/Animator/<name>.fbx`; `serve.py` answers with the rejoined
  file and static packages ship it loose, so the viewer and downloads are
  unchanged.

Assets collapses byte-confirmed identical exported media into one preview
variant within existing asset groups, including images, OBJ, FBX, and video.
The index retains every file row; `h` is the full content SHA-256 and `d` marks
same-kind, same-extension groups also checked for byte equality with bounded
memory. All original filenames and PathIDs remain searchable and appear in
same-content file details. Converted-file equality does not establish original
Unity object equality or ownership; OBJ omits skin weights and blend shapes.
Sprite crops retain their separate texture/crop content evidence. Export files
remain in place.

Matching FBX resources share one item page with all deduplicated resource paths
from `c`/`cs` listed in its details. The optional `fc` key ignores export/instance
labels, placement/joint transforms, preferred angles, pose matrices and bind
matrices; geometry, materials, mesh/bone names, skeleton connections, skin
indices/weights and animation still participate. The pose-preserving `fv` key
ignores the same export/instance labels but retains transforms, poses and bind
matrices; matrix compression alone does not create a difference. Distinct `fv`
keys become named, selectable variants with a placement/pose/skin-binding
difference fact. Selection switches the preview and Download current file to
that variant's original FBX. Resource files also links every original download.
Path/name-only aliases share their variant and list multiple resource paths.
`h` remains the full-file SHA-256. Paths, filenames and PathIDs remain searchable,
and every original `?asset=` link resolves to the correct variant within the
shared item. Distinct FBX LOD content retains its prefab-scoped variants.

OBJ WebGL previews preserve face UVs, authored normals, and `usemtl` draw
ranges. An OBJ without `usemtl` uses a material only when its published links
have one distinct material name; multiple candidates remain neutral. Linked
Unity material relations supply base textures, tint, alpha testing and blending.
Missing UVs keep the affected range untextured. These name-based preview links
do not prove runtime renderer ownership; the software fallback stays untextured.

Alpha-tested materials keep depth writes and discard pixels below their clip
threshold. Queue 2450 does not enable alpha blending; queues above 2500 or an
explicit transparent surface do. Each WebGL frame resets depth writes before
clearing its depth buffer, then uses the published depth setting for transparent
groups.

The material relation's `blend` also carries opaque `tint`, keyword-enabled
`avatar` (base, base tint, additional tint RGB colors), and `emission` (RGB color
times brightness plus optional `textureRel`). WebGL converts avatar base-map
channel masks into the saved palette before lighting. `Show emission` is off
by default so HDR glow does not saturate the display and obscure surface
details. Turning it on adds the stored emission; Model only disables it.
Mapped emission waits for its texture and requires UVs. This static preview
omits game lighting, bloom and runtime material overrides.

FBX mesh controls mark `eyesshadow`, `hairshadow`, and character-context or
terminal `hs` labels as shadows, including matching ancestor models and material
names. Ordinary names such as `hs_machine` and `HS File` remain visible; an
interior `hs` token alone does not establish a shadow part.
`vfxpart` mesh/material names count as VFX. Shadows start hidden; VFX starts
hidden alongside ordinary meshes, but stays visible in effect-only prefabs.
These labels describe preview grouping rather than runtime rendering proof.

When separate parts have different available minimum LODs, FBX starts with
`Best per part` so an available body is not hidden by a weapon's lower LOD
number. The preset groups normalized LOD names within each owning branch;
numeric LOD controls remain available. It is an inspection view, not a claim
about the game's authored LODGroup selection. A hash-matched index `mr` record
shows incomplete source mesh-instance coverage in the resource inspector;
stale or invalid records are ignored.

FBX previews bake connected linear skin weights and binary cluster bind
matrices against the stored skeleton transforms, so skinned meshes show their
exported static pose. Unweighted points retain their mesh placement; rigid
meshes still use the model hierarchy. This does not play animation stacks.

### Decoded

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
Spawner configs, atmospheric NPC records, map configs and world components expose their maintained
reader fields here. Authored actions, positions and conditions retain their
stored-data evidence boundary; native-dependent datasets become unavailable
when the selected build gate fails.
The Buff dataset passes through canonically admitted complete root receipts;
unresolved sources remain visible as framing projections with source links.
Skill records may add authenticated `facts.canonicalRootEvidence` independently
of their derived values. The detail view distinguishes complete stored framing
from unproved recursive field naming; the derived record remains
`structural_only`. Missing or stale canonical evidence suppresses those added
facts rather than promoting the remaining values.

### Updates

Updates shows the comparison of two complete export roots: WebUI-facing
exported text plus image, model, video, and decoded audio assets, never a
change under `webui/`, `reports/`, `memory/`, or `scratch/`. A serialized
payload diffs through its maintained reader and says so (`text_kind`); a
changed file with no diff says why (`text_diff_note`). Path-only relocations
with unchanged content are omitted. Build with `.\build_updates.bat OLD NEW`.

Optional `data/updates/{characters,story,map,gameplay,reference,activities}.json` sidecars add Added/Modified
badges to Story conversation titles, Map zone lists and the selected zone,
and Gameplay entry lists and details. The shared `src/ui/update_badges.js`
loads them without caching. Badges describe changes in linked authored source
records (including shared localized text), not recovered order, native evidence,
or a diff of generated WebUI files. An unavailable or absent sidecar leaves
the page usable without badges. Deleted IDs remain in the sidecars and do
not create current Story conversations, Map zones or Gameplay entries.
Gameplay comparisons follow explicit owner fields: related cost-item and
default-weapon labels do not import other characters, weapon stats or recipes.
Item usage comparisons keep their declared source-field scope. Shared skills
and set definitions still appear for each actual owner.
Equipment compares the selected set's effects, not its sibling membership
list. Linked region, formula-pack and unlock-channel rows supply labels only;
regional development and shop inventories do not count as equipment changes.
Gem point badges use `gem:<groupId>` and compare their pool/stage definitions
and linked labels, including Added for a newly authored point group.
Combat stages use `stage:<DungeonTable key>` in the Gameplay sidecar and expose
list/title badges, source-field comparisons and Version changes. Activities
uses `ActivityTable/<id>` in its schema-3 sidecar, including the page's exact
supporting schedule, stage/task, supply and reward joins. Related labels and
navigation slots are scoped to their owner; sibling configurations are excluded.
Resource comparisons exclude candidate subtrees marked `data-update-files-exclude`.
Loadout pickers apply this to their option lists, while the selected preview
remains eligible; unopened equipment choices are not character resource updates.
Tagged details show an initially expanded, collapsible **What changed** panel
with field paths and previous/current values, filtered to the selected data
language. Added/deleted fields distinguish an absent member from `null`.
Map navigation summarizes every physical variant; detail comparisons show only
the selected variant's source files. Registry entities keep stable ID/slot
boundaries across insertions and reordering. Characters schema 5 joins updates
by exact constituent record ID, with separately labeled merged owners; model
and search aliases do not acquire other identities' changes. Name/evidence and
asset-path comparisons use stable identities, excluding generated sidecar paths.
Comparisons stay visible outside debug mode. Linked file
changes include bounded plain/decoded diffs, file sizes, and previous/current
export links. Reader coverage gaps and truncated previews are stated explicitly.
Missing legacy detail data is explained instead of leaving a tag unexplained.

Story, Text Tables, Map, Gameplay, Gameplay item catalogs, Audio and Assets share
Characters' collapsible **Version changes** filter: Added, Modified and Deleted.
Selections combine with existing filters; selecting multiple statuses matches
any of them, and clearing the selection includes unchanged items again. Counts
are dataset totals (tables for Text Tables), independent of other filters,
except Gameplay's Version changes counts, which follow the selected dataset
and other facet filters while ignoring their own status selection and search.
Text Tables narrows both the table list and its displayed rows. Map filters
zone groups using the same combined variant status as their badge; Audio and
Assets use the same linked-file status as their badges. Missing comparison
data hides this filter and clears its selection. Deleted filters show only entries present in the page's
dataset; they do not reconstruct removed content.

## Verification

Build commands and their contracts live in
[`scripts/README.md`](../scripts/README.md); which workflow owns a changed
input is in [`memory/webui_recovery.md`](../memory/webui_recovery.md). The
shortest loop for frontend work is to run `node --check <file>` for changed
JavaScript and smoke-test the affected page using the existing local server.
Start `python serve.py` only when the default server is absent. Frontend-only
changes need no data rebuild; when builder inputs or publication contracts
change, use the owning page's focused refresh and freshness checks.
The page smoke-test checklist is in
[`memory/webui_recovery.md`](../memory/webui_recovery.md). Its Story media step
uses the fixtures `test_sns_emojicomment`, `test_sns_sticker`, and
`sns_topic_map02_lv005_12002`.

Weapon portraits and galleries follow the exact `ItemTable.iconId` binding,
which may differ from the weapon ID. Story Wiki media follows the same binding
through `assets/story_media.json`'s `wikiItemIcons` map; item IDs and names are
unchanged. Missing authored icon assets do not fall back to the weapon's ID.

Local browser state: Loadout automatically remembers each character's level,
potential, affinity-talent stage, weapon progression/skills, equipment and line
enhancements, plus the character Info/Loadout view.
Accessory slots can copy the other slot's equipment and line enhancements;
the two copies remain independently editable and are saved locally.
Saved IDs and numeric bounds are checked against the current catalog on restore. Affinity talents use the
same stage slider as progression. Wide displays use three columns: character
settings and weapon together, equipment, then all named player attributes.
Abilities precede HP/ATK/DEF; critical stats, Arts Intensity, resistances,
healing/cooldown/charge/poise efficiencies and elemental damage follow.
Remaining named stats appear even without a modifier. Narrow detail panels stack
the columns. Metadata display expressions (including scalar-to-bonus conversion)
are respected. Healing includes Will conversion; physical resistance includes
Agi conversion and the four elemental resistances include Wisd conversion.
Ether has no ability conversion in the native default dispatcher. Movement and
combo cooldown use their separate native scalar attributes at the armed/final
stages. Conversion code/literal/enum drift fails closed pending native review.
Older publications retain configuration-only values with an explicit
ability-conversion exclusion; internal resistance scalar rows do not
duplicate the named resistance rows.
Shared sidebar search, display checkboxes, sort category/direction and facet selections also persist
locally. Reloading resumes local choices; opening explicit page links takes
precedence over saved search/facets. Reset
filters updates the saved values. Existing language/theme, sidebar dimensions,
filter disclosures, page size and SQL-draft storage remain in their own owners.
Storage is optional and scoped to the browser origin; malformed or unavailable
storage falls back to defaults. Pinyin search supports initials such as qsjs,
not full pinyin spellings.

Assets size/name sorts span the complete filtered result list, without source
folder headings overriding their order. Variant groups sum their published file
sizes; a Sprite-led group shows those bytes alongside its crop dimensions.
Story's explicit sorts likewise span missions and data types. Multi-word search
relevance applies only to default Story/path browsing in Story, Assets and
Updates; explicit sort categories take priority. Gameplay retains its documented
sort-within-groups behavior.

Audio caches the current dataset order by sort category and direction, using
one numeric collator. Search and facet changes filter that order and reuse
the facet model's cached values; search input waits 120 ms after typing.
Large audio record normalization yields between bounded work intervals and
discards superseded results before publication.

Audio reuses each summary row's published `linkedFileSearch` rather than
rescanning nested evidence; rows without that field retain direct file search.
The index, manual notes and version comparison load in parallel, followed by
the Event read; the list renders with the completed publication once. With no
selection the detail pane stays empty: the page renders no index-level runtime
or catalog overview, and does not read `scene_backgrounds.json`. Long loops
yield through `WebUI.yieldToMain`, which background tabs do not throttle. A
filter pass skips facet filtering when no chip is active and matches the search
text and manual note separately; detail merges drop the facet and sort caches
only when a facet value or sort key changed. Normal index/shard requests revalidate HTTP cache entries;
explicit retries bypass the cache.

Assets PNG previews offer an opt-in `Ignore alpha / RGB` control. It sets alpha
to opaque on decoded pixels before browser bitmap conversion, preserving RGB
hidden by zero alpha. Original downloads and exported files stay unchanged;
this inspection mode does not reconstruct material shader appearance.
