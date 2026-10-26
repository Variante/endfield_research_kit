# WebUI recovery

This file is the maintenance entry point for the static WebUI. Page-specific
recovery contracts live under [`webui/`](webui/README.md); frontend-only layout
and behavior contracts remain in [`../webui/README.md`](../webui/README.md).

## Active pages

Display names are defined in `webui/README.md`: 人物汇总, 文本表格,
视觉资产 (tab 资产), and 数据解码 (tab 解码 / Decoded). Routing tokens
and publication paths remain independent of these labels.

The shared theme offers Endfield (light, default) and Talos Night (dark), applied
before first paint. Saved Classic or unknown choices fall back to Endfield;
valid saved choices persist across pages and reloads. Assets uses plain preview and information columns; frontend
layout details remain in `webui/README.md`.
Assets' Model only control is a frontend rendering preference; it bypasses
material appearance without changing published geometry or material evidence.
Its transparent-face sorting also stays frontend-only and retains published
material render queues and depth-write settings.
Assets owns its optional collision runtime projection and never writes another
page's data. Admission/native/source gates govern runtime labels separately from
the stored-geometry previews; the page contract is in
[`webui/assets.md`](webui/assets.md).
Its optional stored collider/prefab owner projection also belongs to Assets;
it revalidates scene extraction receipts and preserves the runtime evidence
boundary independently of authored enabled/active settings.
Optional Model-source metadata uses that same Assets publication and source
receipts; it links to Data's last exported raw files without writing Data outputs.

Page title typography is shared in `webui/style.css`; Activities, Audio and
Gameplay's top catalog heading use the same rule as the other list pages,
including the square accent marker in `webui/themes.css`. Its specificity preserves
the common style when feature stylesheets load later.
Primary sidebars expose every filtered match in one continuous scroll range.
`src/ui/continuous_list.js` mounts only viewport rows and overscan for ordinary
catalogs, measures variable heights, and supports keyboard navigation and direct
location. Virtual row wrappers use `overflow: clip` so only the list host owns
scrolling. Gameplay groups retain one collapsible heading; Story, Assets and Audio
keep their existing virtual renderers. Data Files discovers source counts and
fetches only viewport blocks through the existing read-only API, with a bounded
metadata cache and request-generation gates. Right-pane detail pagination stays
independent. No source extraction or publication change is needed.

Primary sidebar search and sorting use `src/ui/sort.js`: the Story-style Search
row and category/direction row share label widths and spacing across pages,
including all Gameplay datasets, Characters and Data's file browser. Dynamic
sidebars preserve their source controls and visibility; reset synchronization
runs after page-owned reset handlers.

Gameplay owns one Items frontend catalog including buildings, alongside entity
views. Item facet headings use the common label/count markup. Enemy filters and
sorting omit rarity, and enemy details use the shared catalog section and card
layout. Building categories and relationships join the item filters; exact
published building/item links decide which rows merge. The owning
[catalog guide](webui/gameplay.md) records the Gameplay items v1 index and current-only routing.
All use shared filter dividers capped at natural filter content height,
with the shared minimum list height. The item catalog is published by Gameplay’s `items` stage. Catalog filter groups use the shared
section binding and facets, including selection counts and collapse persistence.

| Page | Recovery guide | Primary builder |
| --- | --- | --- |
| Story | [`webui/story.md`](webui/story.md) | `scripts.webui.story` |
| Gameplay | [`webui/gameplay.md`](webui/gameplay.md), [`webui/activities.md`](webui/activities.md) | `scripts.webui.gameplay.build_gameplay`; Activities reads the last Text/Assets publications |
| Map | [`webui/map.md`](webui/map.md) | `scripts.webui.map.build_map_recovery_data` |
| Characters | [`webui/characters.md`](webui/characters.md) | `scripts.webui.characters.build_character_data` |
| Text | [`webui/text.md`](webui/text.md) | `scripts.webui.story` |
| Audio | [`webui/audio.md`](webui/audio.md) | `scripts.webui.audio.build_audio` |
| Assets | [`webui/assets.md`](webui/assets.md) | `scripts.webui.assets.build_assets` |
| Decoded (export stores, decoded datasets) | [`webui/data_inspector.md`](webui/data_inspector.md) | `scripts.webui.data_inspector.build_data_inspector` |
| Updates | [`webui/updates.md`](webui/updates.md) | `scripts.webui.updates.build_updates` |

The debug-only Recovery tab is documented in [`webui/recovery.md`](webui/recovery.md).
Gameplay owns eight dataset tabs: Characters, Weapons, Essences, Equipment,
Items, Enemies, Combat stages, and Activities. Items includes buildings and
inline recipes; Activities is a Gameplay subpage with its own recovery guide.

Mission Pipeline is a standalone recovery workflow, not a WebUI page or normal
export stage. Retired Progression and Combat & Projectiles pages stay retired;
their useful data belongs to Gameplay.

Gameplay’s Activities subpage lists ActivityTable and reads supporting
tables as linked details from the last Text reference publication for authored schedules and
tags, plus Assets' optional compact activity_media.json for exact artwork and
fixed-reward icons. Both builders retain their own output ownership; Activities
adds no cross-page build dependency. See [Activities](webui/activities.md).
Activities also reads Gameplay's last battle-stage publication for typed
activity references and stage-to-published-map navigation, without writing page data.
Map retains declared dungeon scene targets even without recovered points;
Gameplay links exact published scene IDs, and Activities preserves each stage's
map association. This remains a last-publication join between independent pages.
Activity mission links read Story's last localized index and mission names via
the shared Story navigation helper. Reference-guide mission fields keep their
stored identity; a navigation target is not a stage-specific playback claim.

Gameplay's item catalogs reuse Story's safe rich-text renderer and raw-tag display setting;
machine flavor text comes from linked items in The Gameplay item catalog’s own publication.
Currency purchase records show base prices, configured discounts and discounted prices, including an explicit no-discount label. Older publications missing discount fields show a refresh notice.
Item shop configurations use a collapsed section with configuration-based
deduplication and omit the section when empty; the [catalog guide](webui/gameplay.md) owns the comparison boundary.
Gameplay items labels sources when linked descriptions or decorative texts differ
and displays identical text once; the owning [catalog guide](webui/gameplay.md)
records the distinction from runtime screen selection.
Gameplay items supplies linked wiki explanations from its own tables to Gameplay
details; displaying them adds no dependency on Story publication.
Story item wiki navigation targets Gameplay's Items catalog; its reciprocal
link checks Story's last published index in the displayed catalog language.
shared facet chips accept optional decorative icons.
Shared facet chip counts are dataset totals; combined groups and search can
return no matches even when a chip has a positive count. Assets documents this
in its chip tooltips and empty-list message (see [Assets](webui/assets.md)).
Assets OBJ and FBX previews share background and model color controls; see
[frontend behavior](../webui/README.md#assets).
Assets' optional collision source maps to its own `webui/data/assets/collision/`
publication, with the source root retained in the index and resources package.
It does not replace canonical render exports or establish cross-page ownership.

Map navigation uses `#map`, including Story and Gameplay links and the packaged
WebUI route allowlist.

Gameplay has one dataset bar for Characters, Weapons, Essences, Equipment,
Items, Enemies, Combat stages and Activities. Main Gameplay navigation opens
Characters while explicit dataset links retain their target. The shared routing controller
leaves the root URL unchanged on initial entry and updates routes when the user
switches pages/datasets, retaining existing local selections/settings. Explicit links still work. It
guards Activities URL writes by the active dataset and visible panel, so shared
control restoration cannot redirect a Characters refresh. It
loads all three indexes together on entry and refreshes them together for
language changes/retries; counts no longer depend on visiting each catalog.
Details remain selection-driven and publication ownership stays with each
builder. Combat stages
owns its Gameplay publication and Table inputs; an explicitly labeled preview
may reuse the last published Text/Data/Assets/Gameplay rows without reading an
unfinished export or creating a cross-page build dependency. Data's explicit
`load_published_snapshot` validates complete publication framing but claims no
export freshness; native-backed consumers still supply selected-native gates.
Ordinary `load_dataset` consumers retain source signature/size validation.
Combat stages distinguishes dungeon-selected hosts from shared scene data and
shows stored counts/timing/Buff references with their runtime boundary.
See [Gameplay](webui/gameplay.md).
Equipment manufacturing reads The Gameplay item catalog’s last published
item/icon lookup for thumbnails; neither builder writes the other page's
publication (see [Gameplay](webui/gameplay.md)).
Character, Weapon, Essence and Equipment lists omit repeated kind badges.
Entity and catalog sidebars reuse the same header renderer for entry counts and filter actions, without repeated dataset titles.
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

Building details within Items keep the catalog image and large title, replace tags with
gray metadata including dimensions and power, and share Equipment's crafting cards and the Assets strip,
including combined building/item records. Catalog headers omit the repeated kind
subtitle and place IDs in metadata; the catalog evidence notice is removed.
Shared asset strips keep bounded thumbnails and wrap images and model links within the detail width.
Gameplay asset thumbnails and their enlarged previews identify images by the
complete source filename, with wrapping captions beneath the thumbnail.
Thumbnail captions are plain text and thumbnails open the enlarged preview.
Only Gameplay enlarged-image captions link to the exact Assets entry; ordinary navigation
closes the popup, while modifier clicks keep the native link behavior.
Gameplay record-item headers link to Audio events using exact SpaceshipMusicTable
keys and musicEvent/musicEventSample references; playable-media availability
remains determined by the Audio publication.
Audio's optional `lang/<LANG>/audio/record_media.json` supplies decoded record
media to the same Gameplay Assets section. Empty media stays hidden; this exact
record-table join does not enable unrelated Gameplay sound sidecars or players.
Spaceship exhibit items join SpaceshipShowcaseItemTable.resPath to model
container memberships in the last Assets publication using exact prefab names
and Unity type/PathID. Assets owns those memberships; Gameplay owns the links.
Factory device/logistics/decoration model links are also Gameplay-owned. Their
asset-ref stage reads the effective object index and AssetMap config memberships,
joins rendering Mesh PPtrs to the last Assets publication, and preserves
conditional evidence for segmented resource-prefix owner candidates.
Item portraits and Assets cards share the asset sidecar. Authored binary-table
icon references take priority over filename inference and manual selections.
Reading art remains supplemental; missing declared icon assets leave a text-only
header, while directly authored generic icons stay visible.
Equipment shares Weapon's reading layout and asset strip. Its
manufacturing view groups separate Recipes input → output rows in one card and hides undecoded
unlock metadata and pack membership. Gameplay's tracked
`webui/overrides/gameplay_assets.json` supplies explicit model selections for
the asset-ref publication; manual selections remain distinct from source proof.
Its Items tab combines the Gameplay items catalog with
Gameplay's published use effects and rewards in the same displayed language.
Item illustrations, card themes, stickers and avatar art follow explicit
Gameplay items media bindings through Gameplay's asset sidecar. They render in the bottom Assets section with the shared Gameplay heading
and image/model strip, including the weapon/Essence rounded borders and gray backgrounds.
The sidecar consumes the Gameplay items and Assets publications; no builder
writes another page's files.
Both builders retain their own output paths and export scopes; run
`export.bat gameplay` to refresh the page data.
Gameplay's Items sidebar keeps filter visibility and reset together;
both actions stay available when collapsed.
Their details end with the shared image gallery, including displayed Gameplay items
icons and published Gameplay item assets, deduplicated by path.
Audio and Data share the dataset-tab styling below their sidebar title.
All range thumbs share a circular theme-colored outline, including custom
range controls and visible media-player seek handles.
All Gameplay detail headers use the shared image and large-title shell with gray metadata; character Data / Loadout controls follow the character name in the title row.
Weapon details reuse character section headings and asset thumbnails, with
spacing in place of horizontal section dividers.
Essence details reuse that layout, with three term columns, compatible weapons
and image assets; the world-level cost section is omitted.
Story completion rewards use its own mission/Table inputs; their item links
open Gameplay's last published Items catalog without adding a page dependency.
Resolved item rewards render in a separate block titled Mission Completion Rewards;
empty or unavailable item lists show no block. Map links appear as small gray text
below the Story detail title, using Map's last published mission index.
Their names and IDs enter Story's own localized search sidecar before detail loading.

Updates owns optional `updates/{characters,story,map,gameplay,reference}.json`
sidecars. Page consumers add change badges and old/current detail panels to
their current publications, including grouped Map variants and linked files;
the comparison never writes into another page's dataset or alters its
recovery evidence. See [Updates](webui/updates.md) for the comparison boundary.
Every page with change tags also offers Characters-style Version changes
facets, using the badge's status and combining with the page's other filters.
Text Tables filters table membership from the reference sidecar and filters
loaded rows by their exact source key. Audio and Assets share linked-file
status aggregation; Map uses the displayed group's combined variant status.
Unavailable comparisons hide the facets without changing the published data.

## Export flow

Choose the smallest workflow that owns the changed input:

| Situation | Command |
| --- | --- |
| First setup | `.\setup.bat` |
| Rebuild every page from current `export_full/` | `.\export.bat` |
| Rebuild only the pages a change affects | `.\export.bat map audio` |
| Extract what every page reads, then build every page | `.\export.bat --from-game` |
| Extract and build one page | `.\export.bat map --from-game` |
| Lean Story/Text extraction (the setup path) | `.\export.bat story --from-game` |
| Extract every structured block and Unity class | `.\export.bat debug --from-game` |
| Compare two complete exports for Updates | `.\build_updates.bat OLD NEW` |
| Serve / package | `python serve.py` / `python -m scripts.webui.package` |

`export.bat` is grouped by page and delegates to `python -m
scripts.webui.export`. Do not use `--from-game` for a data-only rebuild.

**What a page needs is declared once, per build task, in
`scripts/webui/pages.py`.** A task names the export inputs it `reads` (must
exist and be current), the ones it reads when present (`optional`), the
producer tasks of the same page it `needs`, and the tasks it follows when
both run (`after`). A page is a set of root tasks; a run takes their closure
over `needs`, extracts the union of those tasks' inputs, and checks exactly
those inputs.

**Pages are independent.** A page run builds only that page. What it shows
from another page -- Story's voice lines from Audio, Map's render colours and
the Characters and Gameplay asset links from the Assets index, Story and
gameplay output in Audio -- is that page's last publication, or absent, and
`--show-plan` names those pages. `check_pages_independent` refuses a `needs`
edge into another page. This is sound only because no builder writes another
page's output: Audio publishes what it links to a Story conversation (line
voice files, event audio, dialog lifecycle hooks) as its own
`lang/<code>/audio/conv/<key>.json` sidecar, which the Story page merges at
load, so a Story rebuild keeps its voice and Audio never edits `conv/`. A new
cross-page link takes the same shape.

Map encounters and Gameplay skill references consume Data's last publication
through the shared publication validator. Each publishes only its own compact
sidecars, authenticates source signatures and any required selected native
inputs, and exposes missing or stale families visibly. An optional `after`
edge orders a combined build; it does not add Data to a standalone page run.
Character appearances similarly use the last Story publication for exact
source verification in the browser, without a Story build dependency.

`story` extracts text only (tables, JsonData, the Story Unity classes); the
video override gate reports its stem checks as skipped when no video was
exported. `story-media` is the same page with its images and videos: it also
extracts video, Texture2D and Sprite and publishes `story_media.json`. The
Data page serves every decodable output the other pages do not show
(everything except their media), so an all-page extraction already equals
`debug`, which extracts every structured block and Unity class.

The flow is:

1. Resolve paths from `endfield_paths.bat`, overridden by explicit flags.
2. With `--from-game`, export the plan's scope in one AnimeStudio run. Every
   AnimeStudio run writes VFS indexes before the Unity overlay skip lists,
   including first-time Story-only setup, and a run that exports MonoBehaviour
   and PlayableDirector republishes the object index.
3. Check that every input the plan reads came from the installed build: the
   exporter stamps each published structured block, Unity class and the asset
   maps (`meta/extraction/provenance.json`), so an output left over from an
   earlier build fails the check and is named, while an absent optional input
   only degrades its builder.
4. Run ready tasks in the build graph within the job limit. Story, Assets,
   Gameplay items, projectile recovery and Data can start together; later tasks
   start as soon as their selected dependency edges succeed. The registry
   owns this order; `python -m scripts.webui.export_diagram` regenerates the
   scope matrix and dependency depths in `res/export_pages.svg`.
5. Write step timings and process-tree memory benchmarks under
   `reports/export/`.

`--webui-jobs N` bounds concurrent builders and supplies Map's internal
workers. `--asset-jobs N` limits AnimeStudio workers. Use
`--full-source-graph` only for exhaustive Unity object/PathID investigation.

Updates compares saved complete exports with `build_updates.bat OLD NEW`;
export runs do not manage comparison snapshots or publish Updates.

## Shared contracts

- Shared loaders report measured download progress within a named stage;
  parsing, preparation and rendering stay indeterminate. See
  [`webui/README.md`](../webui/README.md) for the frontend contract.
- Generated data belongs in `webui/data/`; never hand-edit it. User-maintained
  inputs belong in `webui/overrides/`, and export runs never replace Story
  order or manual option overrides.
- A schema change updates producer and consumer together. Missing optional
  sidecars render as unavailable or degraded, never as a silent empty success.
- Normal navigation contains only the nine main pages above; debug state may
  reveal raw sources and recovery evidence, but Story issue/method filters stay
  visible.
- Evidence types remain distinct: authored reference, recovered relation,
  inferred ownership, runtime observation, and user annotation are not
  interchangeable.
- Gameplay does not load or render the generated projectile/audio sound
  sidecars while their ownership model is under review; audio investigation
  remains on the Audio page.
- List-page layout, pagination, and search semantics are shared frontend
  contracts in [`../webui/README.md`](../webui/README.md).
  Text applies a smaller rendering budget and bounded raw-file previews; its
  complete-source access and browser size limits are documented in
  [Text](webui/text.md).
  Linked file names stay searchable before detail loading; Audio publishes
  Story's audio-file search text in its own conversation index, alongside the
  per-conversation sidecars, without rewriting Story outputs.
- Reuse an existing `http://127.0.0.1:8765/` server before starting another.

## Verification

After a focused edit, run the owning builder and its focused tests. At a
publication boundary, run the canonical wrapper, inspect
`reports/export/webui_build_steps_latest.md` and
`reports/export/export_full_summary.md`, then smoke-test every active page.
Use the serve/package workflow only when browser or archive validation is
required.

The frontend smoke test is, concretely: load every normal page and read the
browser console; check Story reset, the recovery filters, and the SNS
emoji/sticker fixtures named in [`../webui/README.md`](../webui/README.md);
open one playable character and one enemy in Gameplay and verify variants,
progression, skills, projectiles, and asset links; check deep links and media
playback; and confirm that an absent optional input produces a clear degraded
state rather than an empty success. On each long-list page, also change the
page size, move between pages, then filter and confirm the list returns to
page one without losing the current detail unexpectedly.

Changing counts and per-build inventories belong in `reports/`; page guides
record only stable recovery logic, evidence boundaries, and the highest-value
gaps.

## Packaging contract

`scripts/webui/package.py` emits four matching archives; the commands are in
[`../scripts/README.md`](../scripts/README.md). The main archive owns WebUI
code and generated text data. The `-media` archive owns images/videos
referenced by Story, Text, Map, Characters, and Gameplay plus their compact
asset index. The `-audio` archive owns FLAC files referenced by those pages.
The optional `-resources` archive owns every file the Assets page lists, the
remaining FLAC set, and the complete Audio/Assets resource indexes; assets
referenced by normal pages are duplicated there so the Assets page works from
the resources archive alone. With no selection the archives publish atomically
in main, media, audio, then resources order; an explicit selection uses the
caller's order. Already-compressed media is ZIP-stored instead of being
recompressed. Each archive includes a UTF-8 Chinese usage note; extract
resources last because its complete asset index replaces the compact
media-only index. Decoded Data-page datasets are local output and are not
packaged.

Shared update panels accept optional owner labels so grouped Gameplay enemies
retain each configuration’s identity alongside its source comparison.

Shared frontend sorting uses adjacent category and direction selects through
`webui/src/ui/sort.js`; direction has an accessible name without a visible label
and remains selectable for every category, including default ordering.

Updates owns the optional activities.json source-row comparison sidecar, reused
from the gated Reference diff for Activity*Table and CheckInRewardTable. Activity
change badges read this publication without modifying their current catalog.

Assets collapses byte-confirmed identical exported media into one preview
variant within existing asset groups, including images, OBJ, FBX, and video.
The index retains every file row; `h` is the full content SHA-256 and `d` marks
same-kind, same-extension groups also checked for byte equality with bounded
memory. All original filenames and PathIDs remain searchable and appear in
same-content file details. Converted-file equality does not establish original
Unity object equality or ownership; OBJ omits skin weights and blend shapes.
Sprite crops retain their separate texture/crop content evidence. Export files
remain in place.

Gameplay items relationship display preserves original recipe-method identity and
all goods provenance when grouping matching shop configurations; see the
[Gameplay guide](webui/gameplay.md) for the evidence boundary.

Item storage limits appear in header metadata only for finite values greater than one. Equal storage/backpack limits share one label; different limits retain explicit storage/backpack labels. Building buffer limits remain separately labeled. Sentinel/default values are omitted without claiming unlimited storage. Raw item/building/recipe configuration remains available behind Show debug info; source identifiers, booleans and anonymous enums are not normal-view metadata.

Weapon and equipment records link both ways between Gameplay’s Items and their respective datasets using exact matching IDs in the displayed language. Header buttons appear only when the target exists in the current publication, share the Story Wiki button style, and sit beside it in one wrapping row using shared dataset routing.

Gameplay character Loadout uses searchable image choices for weapons and
slot-compatible equipment. Name fragments, suit names, record aliases and
pinyin initials filter the choices; published Gameplay asset links provide
thumbnails. Browser pinyin collation supplies initials without external data,
with polyphonic-name aliases remaining explicit. Search and image selection do
not change the validated attribute formula or its excluded 基质词条 boundary.

Gameplay character metadata and facets distinguish elemental type from main
and secondary abilities (`mainAttrType` / `subAttrType`). Loadout equipment
terms keep the authored main/secondary target label beside its resolved ability;
changing character changes the resolved label, never the original target scope.
Equipment main-ability terms use bold text with a background; secondary-ability terms use only the same background. Both retain their existing text colors, without underlines or borders. Character Loadout applies the same treatment to equipment attributes resolved against the selected character, with explicit main/secondary labels; combined targets use the main-ability bold treatment. These are display cues and do not change calculation or target scope.

Assets publishes Story Wiki's authored item-to-icon bindings as `wikiItemIcons`
in `story_media.json`, read from the current exported ItemTable. Gameplay's
weapon rows publish the same `iconId`, and the asset join follows that exact
binding. This keeps Items, weapons, Loadout and Story Wiki thumbnails consistent
when a weapon's icon basename differs from its entity ID.

Local preferences use optional browser storage. `core/storage.js` owns shared
sidebar search/sort controls; `ui/facets.js` separates stored groups by stable
container ID and removes stale locally restored values against the loaded
catalog. Reloading resumes saved choices; newly opened explicit page links override saved
sidebar state. Existing page-specific
storage (SQL drafts, language/theme, dimensions, disclosures and page size) stays
with its owner. Gameplay Loadout stores validated per-character choices and its
Info/Loadout view; affinity talents use a stage slider. The wide Loadout layout has character settings plus weapon in the first column,
equipment in the second and attributes in the third; narrow detail panels stack
these columns. All named player attributes remain visible in the requested
ability/core/secondary order. Metadata expressions convert scalar values to
bonuses or reductions. Unmodelled derived hooks show explicitly partial
configuration values instead of silently disappearing or claiming completeness.
Gameplay publications with the v2 native formula include Will healing,
Agi/Wisd resistance, movement and combo-cooldown conversion stages. Code-window,
literal and enum authentication owns that calculation boundary; older
publications keep their partial-value labels until rebuilt.
Accessory 1/2 offer reciprocal copy buttons for equipment and enhancement
choices. Copying creates independent enhancement state, refreshes calculations
and saves the destination; an empty source disables its copy button.

Page activation uses the shared `webui:view-changed` event; Text, Updates and
Recovery do not also bootstrap from tab clicks and hash events. Gameplay
ignores delayed same-language Story announcements, while actual language
changes and explicit retries refresh the catalogs. Characters and Activities
share pending requests for the requested language. Audio search and facet
changes reuse dataset sorting and cached facet values; large record
normalization yields to browser input and rejects superseded generations.
