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

Nine tabs, in navigation order. `data-view` is the tab token in `index.html`
and the value of `document.body.dataset.activeView`.

| Page | `data-view` | Scope | Behavior contract |
| --- | --- | --- | --- |
| Story | `story` | Reconstructed dialog, SNS, radio, local branch overviews, cutscenes, media, and evidence-typed order | `app.js` |
| Map | `map-recovery` | Authored world-space evidence, encounters, patrols, NPCs and scene conditions with minimap, model, point, and water layers | `src/features/map_recovery/index.js` |
| Characters | `characters` | Identity groups, complete source appearances, verified Story links, related assets, and live overrides | `src/features/characters/index.js` |
| Gameplay | `gameplay` | Characters, equipment, enemies, items and their effects, recipes, machines, progression, skills, projectiles, and assets | `src/features/gameplay/{tabs,index}.js`, `src/features/production/index.js` |
| Text | `reference` | Searchable localized table/reference rows and configured achievement/activity targets and rewards | `src/features/reference/index.js` |
| Audio | `audio` | Wwise Events/media, authored contexts, decoded playback candidates, and recovery state | `src/features/audio/index.js` |
| Assets | `assets` | Exported images, models, video, and metadata | `assets.js` |
| Data | `data-inspector` | Files list over the export stores, loose and undecoded export files, and decoded datasets, plus a SQL console | `src/features/data_inspector/{stores,index}.js` |
| Updates | `updates` | Exported game-data changes between two complete versions | `src/features/updates/index.js` |

`recovery` is one more, debug-only tab revealed by `Show debug info`
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
`#<view>` also selects a tab: `#projectiles` falls back to Gameplay.
Legacy `#production` links select the corresponding Gameplay catalog and
normalize to `#gameplay`, preserving the selection and filters. Unknown hashes
fall back to Story.

| Parameter | Selects |
| --- | --- |
| `?ui=` / `?uiLang=` | interface locale |
| `?lang=` | data language |
| `?story=` / `?conv=` | Story conversation key |
| `?line=` / `?cid=` with `?story=` | Focus a rendered Story line or content ID and open containing disclosures; `cid` disambiguates repeated line IDs |
| `?asset=` | Assets entry by relative path |
| `?audio=` + `?audioKind=` | Audio record (`events` or a media shard) |
| `?gameplayKind=` (+ `?gameplay=` / `?gameplayId=` / `?entry=`) | Gameplay dataset (`character`, `weapon`, `equipment`, `item`, `enemy`, `recipe`, `machine`) and selected entity; existing item links open the combined Items catalog |
| `?productionKind=` + `?productionId=` (+ `?productionQ=`, repeated `?productionType=` / `?productionCategory=` / `?productionTag=`, `?productionSort=`) | Gameplay's item, recipe or machine catalog (`items`, `recipes`, `machines`), selected record, search, facets, and order; old medal item IDs resolve to their achievement group |
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
| `src/ui/{media_player,splitter,filters,facets,sort,pagination,update_badges}.js` | shared media player, resizable splitters, filters, sorting, pager, and version-change comparisons |
| `app_labels.js`, `app_tree.js`, `src/features/story_triggers.js`, `app.js` | Story/Text labels, tree rendering, trigger evidence, Story page |
| `src/features/story/{branches.js,branches.css}` | Local option and SNS branch overviews; typed routes, manual annotations, and unresolved continuations |
| `assets.js` | Assets page |
| `src/features/characters/{index.js,appearances.js,style.css}` | Characters view, collapsible appearance records with source-checked Story navigation, and runtime overrides |
| `src/features/gameplay/{labels.js,loadout.js,mechanics.js,skill_refs.js,index.js,tabs.js}` | Gameplay entity details, loadout, semantic summaries, authored skill references, item effects, and shared dataset navigation |
| `src/features/production/{index.js,style.css}` | Gameplay's item, recipe and machine catalogs using shared facets, sorting, pagination, and Data file links |
| `src/features/audio/{index.js,style.css}` | Audio evidence browser |
| `src/features/map_recovery/{index.js,encounters.js,style.css}` | Map view and selection-only authored encounter overlays |
| `src/features/next_views.js` | shared page-bootstrap wiring |
| `src/features/reference/{files,index}.js` | bounded file reads/cache and localized Text Tables browser |
| `src/features/updates/index.js` | Updates page |
| `src/features/recovery/{index.js,style.css}` | debug-only Recovery progress page |
| `src/features/data_inspector/{index.js,stores.js,style.css}` | Data page: `stores.js` owns the mode switch, deep links, and the Files/SQL modes; `index.js` is the decoded-dataset source (catalog, matching, row markup, record viewer) |

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

Gameplay separates characters, weapons, equipment, items, enemies, recipes and
machines into dataset tabs; only the selected dataset's filters are shown.
Items uses the complete Production item catalog, adding the matching Gameplay
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
and links to its recipe detail.
Character breakthrough costs and potential values stay expanded. Character
avatar items use square head images; filled containers include their liquid/gas
icons, and medal tiers use their achievement artwork. Single-tier medals show
Level 1. Recipes producing the same complete output item set share one entry,
preserving each method's inputs, quantities and configured production time.
Conditions and stored configuration stay expanded in two columns on desktop.
Recipes also filter by their produced items' categories. Achievement medals
share one entry per proved tier group, keeping every tier's description and
target; medal filters use the authored achievement categories. Medal list rows
and detail headers show every tier and plated icon on the left. Matching limited
items linked by `LTItemTable` also share an entry, combining their relationships
and retaining navigation/search through either original identifier. These catalogs use
the shared update badges and old/current source-field details. Gameplay list
rows reuse its optional asset-reference images as lazy thumbnails; characters
use horizontal face banners, following the selected Administrator gender.
Item picture records (`item_pic_*`) also show their matching `pic_*` illustration
above the description, preserving its proportions and shared image previews.
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
groups; pagination counts records and repeats headings on continued groups.
Group headings fold their records and retain their state while browsing;
Locate current file opens the selected record's group. Enemy update filters,
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
webui/data/production/manifest.json
webui/data/lang/<LANG>/production/{index.json,items/*,recipes/*,machines/*}
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
webui/data/assets/{index,gameplay_refs,story_media,table_owners,videos}.json
webui/data/data_inspector/index.json
webui/data/data_inspector/datasets/<datasetId>/{index,records.*}.json
webui/data/updates/latest.json
webui/data/updates/{characters,story,map,gameplay}.json
webui/data/recovery/index.json
webui/data/story_order_ocr.json
webui/data/mission_pipeline/index.json
```

Builders may add compact sidecars, but each page must tolerate an absent
optional sidecar and display an explicit degraded state when the omission
matters. Schema changes must be coordinated with their frontend consumer.

Characters verifies an appearance's source row, speaker and localized text
against the last Story publication before navigating. Story branch overviews
retain manual and unresolved evidence labels; a local route does not establish
an overall playthrough. Text guides retain exact table references and source
paths, keep condition codes in disclosures, and paginate rendered rows while
searching every loaded row. Targets, rewards and time ranges describe stored
configuration, not current availability or player progress.

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
- Sorting places category and direction selects on one row: `Category` selects
  the comparison field; the direction select has no visible label and always
  allows ascending or descending order, including default ordering. Shared
  `src/ui/sort.js` controls preserve each page's sort values and handlers,
  combine direction-bearing options into one category, and reverse unpaired
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

- Mission summaries show notes and localized completion reward items with
  small item icons, quantities and links to Gameplay's Items catalog, including
  missions without notes. `mission/*.json` carries `extras.completionReward`, joined from the
  mission-level `MissionRuntimeAsset.rewardId` through `RewardTable` and
  `ItemTable`; quest-step rewards are excluded. Missing referenced rewards
  remain visibly unavailable; random rewards are labeled separately. Icons use
  the authored `ItemTable.iconId` and the optional Story media lookup.
  Story search includes completion reward names and item IDs for each mission's
  entries, without opening mission details first.
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

### Gameplay

Gameplay owns character progression, equipment, enemies, skills, Buffs,
projectiles, and assets, and hosts the independently published Production item,
recipe and machine catalogs. Dataset paths and builder ownership remain
separate: `export.bat gameplay production` refreshes all Gameplay tabs from
the existing export. Character and enemy details use
an overview and local section navigation. Characters lead with parsed mechanisms,
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
`attributeCalculation` (`loadout.js`). Evidence limits:
[`memory/webui/gameplay.md`](../memory/webui/gameplay.md) and
[`memory/game_data/gameplay_semantics.md`](../memory/game_data/gameplay_semantics.md).

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
The Audio overview keeps this static installed-package inventory separate from
capture observations. A complete current VFS/AKPK gate supplies package and
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
control meaning. Direct-effect rows stay in lazy media details; Bus parameters
remain in the unique shared catalog. What each state refuses to claim is in
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
  schema 2 with one `meshes` array per entity base. Newly built Mesh rows record
  `identityEvidence`: `exact_level_hlod_key` or `name_family_candidate`.
  The latter is preview geometry with an exact instance matrix but unproved
  prefab-to-Mesh ownership; Map labels it as such. Older sidecars without the
  field are unclassified candidates when rebuilt. Already published streaming
  maps without `surfaceEvidence` show a legacy ungraded badge until refreshed.
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

### Assets and Text

- Assets lists images, video, OBJ, and FBX, not exported JSON: every such
  document is a Data-page store row, and a material links to its Data-page
  document. The optional `Table owner` fact requires an exact whole-stem match
  in an asset-bearing field.
- Assets chip counts are totals over grouped asset entries. Type, category,
  source, and search can narrow the result to zero; chip tooltips and the
  empty-list message explain this and point to clearing search or resetting.
  The filter panel scrolls within half the viewport height so expanding the
  category catalog keeps the results visible.
- Sprite images are crop documents over their textures, still linked as
  `.../game/Unity/Sprite/<name>.png`; `serve.py` answers with the crop
  document and `sprite_worker.js` renders it pixel-identical to AnimeStudio.
  Without the worker (no secure context) Sprites do not display.

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

### Updates

Updates shows the comparison of two complete export roots: WebUI-facing
exported text plus image, model, video, and decoded audio assets, never a
change under `webui/`, `reports/`, `memory/`, or `scratch/`. A serialized
payload diffs through its maintained reader and says so (`text_kind`); a
changed file with no diff says why (`text_diff_note`). Path-only relocations
with unchanged content are omitted. Build with `.\build_updates.bat OLD NEW`,
or let `.\export.bat --changed-only` compare with the last successful sync.
An unchanged sync preserves the last comparison and its badges.

Optional `data/updates/{characters,story,map,gameplay,production,reference}.json` sidecars add Added/Modified
badges to Story conversation titles, Map zone lists and the selected zone,
and Gameplay entry lists and details. The shared `src/ui/update_badges.js`
loads them without caching. Badges describe changes in linked authored source
records (including shared localized text), not recovered order, native evidence,
or a diff of generated WebUI files. An unavailable or absent sidecar leaves
the page usable without badges. Deleted IDs remain in the sidecars and do
not create current Story conversations, Map zones or Gameplay entries.
Tagged details show an initially expanded, collapsible **What changed** panel
with field paths and previous/current values, filtered to the selected data
language. Added/deleted fields distinguish an absent member from `null`.
Map groups include changes from every physical variant, labeled by source
and owner; their comparison stays visible outside debug mode. Linked file
changes include bounded plain/decoded diffs, file sizes, and previous/current
export links. Reader coverage gaps and truncated previews are stated explicitly.
Missing legacy detail data is explained instead of leaving a tag unexplained.

Story, Text Tables, Map, Gameplay, Production catalogs, Audio and Assets share
Characters' collapsible **Version changes** filter: Added, Modified and Deleted.
Selections combine with existing filters; selecting multiple statuses matches
any of them, and clearing the selection includes unchanged items again. Counts
are dataset totals (tables for Text Tables), independent of other filters.
Text Tables narrows both the table list and its displayed rows. Map filters
zone groups using the same combined variant status as their badge; Audio and
Assets use the same linked-file status as their badges. Missing comparison
data hides this filter and clears its selection. Deleted filters show only entries present in the page's
dataset; they do not reconstruct removed content.

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
