# WebUI recovery

This file is the maintenance entry point for the static WebUI. Page-specific
recovery contracts live under [`webui/`](webui/README.md); frontend-only layout
and behavior contracts remain in [`../webui/README.md`](../webui/README.md).

## Active pages

| Page | Recovery guide | Primary builder |
| --- | --- | --- |
| Story | [`webui/story.md`](webui/story.md) | `scripts.webui.story` |
| Map | [`webui/map.md`](webui/map.md) | `scripts.webui.map.build_map_recovery_data` |
| Characters | [`webui/characters.md`](webui/characters.md) | `scripts.webui.characters.build_character_data` |
| Gameplay | [`webui/gameplay.md`](webui/gameplay.md) | `scripts.webui.gameplay.build_gameplay` |
| Production | [`webui/production.md`](webui/production.md) | `scripts.webui.production.build_production` |
| Audio | [`webui/audio.md`](webui/audio.md) | `scripts.webui.audio.build_audio` |
| Assets | [`webui/assets.md`](webui/assets.md) | `scripts.webui.assets.build_assets` |
| Text | [`webui/text.md`](webui/text.md) | `scripts.webui.story` |
| Updates | [`webui/updates.md`](webui/updates.md) | `scripts.webui.updates.build_updates` |
| Data page (export stores, decoded datasets) | [`webui/data_inspector.md`](webui/data_inspector.md) | `scripts.webui.data_inspector.build_data_inspector` |

Mission Pipeline is a standalone recovery workflow, not a WebUI page or normal
export stage. Retired Progression and Combat & Projectiles pages stay retired;
their useful data belongs to Gameplay.

Production reuses Story's safe rich-text renderer and raw-tag display setting;
shared facet chips accept optional decorative icons.

Gameplay, Production, Audio and Data use the same dataset-tab bar directly below their
sidebar title. Gameplay tabs separate entity kinds and keep subtype filtering
within the selected dataset; generated data remains Gameplay-owned.

Updates owns optional `updates/{characters,story,map,gameplay}.json`
sidecars. Page consumers add change badges and old/current detail panels to
their current publications, including grouped Map variants and linked files;
the comparison never writes into another page's dataset or alters its
recovery evidence. See [Updates](webui/updates.md) for the comparison boundary.

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
| Apply changed installed VFS files locally, then rebuild every page | `.\export.bat --changed-only` |
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
4. Run the build graph: Story first where later tasks read it, then Map, Assets,
   Characters, Gameplay, the curated source graph and its consumers, Audio and
   the Data page's decoded datasets, each as soon as its edges succeed.
5. Write step timings and process-tree memory benchmarks under
   `reports/export/`.

`--webui-jobs N` bounds concurrent builders and supplies Map's internal
workers. `--asset-jobs N` limits AnimeStudio workers. Use
`--full-source-graph` only for exhaustive Unity object/PathID investigation.

`--changed-only` is a local refresh, not an Updates comparison. It runs the
same complete build of every page while reusing existing bundle-derived
outputs, asset maps and decoded audio, which its freshness check reports as
reused rather than current. Only changed structured VFS logical files are
extracted; it neither calls the Updates builder nor advances any
previous-export/Updates baseline. Its private VFS snapshot commits only after
all publication stages succeed.

## Shared contracts

- Generated data belongs in `webui/data/`; never hand-edit it. User-maintained
  inputs belong in `webui/overrides/`, and export runs never replace Story
  order or manual option overrides.
- A schema change updates producer and consumer together. Missing optional
  sidecars render as unavailable or degraded, never as a silent empty success.
- Normal navigation contains only the eight pages above; debug state may
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

Shared frontend sorting uses adjacent category and direction selects through
`webui/src/ui/sort.js`; direction has an accessible name without a visible label
and remains selectable for every category, including default ordering.
