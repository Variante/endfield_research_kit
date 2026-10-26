# Updates page recovery

## Purpose

Updates reports exported game-data changes between one saved previous export
and one current complete export. It must never report repository documentation,
WebUI source edits, generated reports, or scratch data as game updates.

## Inputs and recovery flow

Keep a complete previous export before refreshing the current one, then use
`build_updates.bat OLD NEW`. Both `layout.json` markers must declare `complete`.
A `writing` marker blocks comparison because it can describe interrupted
publication; establish that the export completed before repairing its marker.
Compare matching extraction coverage: newly exported data families can appear
as additions even when the client content did not change. Export runs do not
automatically publish Updates or advance a comparison baseline.

1. Resolve `OLD` and `NEW` complete export roots from the command line or
   `endfield_paths.bat`.
2. Refresh the cached previous-export baseline when the saved old export was
   replaced.
3. Scan the same focused text and asset roots on both sides
   ([`scanner`](../../scripts/webui/updates/scanner.py)). Asset changes use fast
   size fingerprints by default; `--exact` hashes contents.
4. Build both Characters catalogs with the current Characters builder, one per
   export, from that export's own tables and converted media (no Story actor
   registry), and diff them as a Characters-page sidecar
   ([`characters`](../../scripts/webui/updates/characters.py)), without
   feeding the result back into character recovery or grouping.
5. Compare linked authored Story, Gameplay and Map source records with the
   same projection for both exports and publish their page sidecars
   ([`page_records`](../../scripts/webui/updates/page_records.py)).
6. Publish the feed; scanner cache and history remain under
   `.game-data-tracker/`.

The normal build publishes every matching entry and the page paginates the
complete set. `--sample-limit N` is only a diagnostic cap (`0` is unlimited);
an oversized text diff preview is bounded without removing its entry.

**Diffed text is chosen by content, never by extension.** Most of `game/Json`
is serialized MemoryPack under a `.json` name. Plain text diffs as itself; a
serialized payload renders through the maintained `scripts.game_data` reader
that [`decoded_payloads`](../../scripts/webui/decoded_payloads.py) routes it
to; an unrouted or oversized payload gets no text. "Lines" count the text
actually diffed, and an unchanged decoded view of a changed file is reported as
a change outside the reader's coverage, never as no change. Changing the
routing or a reader's coverage changes cached text, so refresh the
previous-export baseline afterwards.

**Relocation joins are fail-closed.** Unity exports whose generated
`_p<PathID>` suffix differs pair only one-to-one by stable kind, extension, and
suffix-stripped path; unmatched decoded audio pairs by byte-identical content,
then FLAC by STREAMINFO format, sample count, and decoded-PCM MD5. Same-name
pairs win, and a content-only or PCM-only pair must be unique unless an
unchanged parent folder makes each duplicate one-to-one. Unchanged content is
omitted as path-only churn; a stable Unity identity with changed bytes stays
one `modified` entry. Obsolete numeric AudioDialog copies are suppressed only
under the exact external-source hash, single canonical asset, and identical
bytes rules in `redundant_audio_dialog_copies`
([`build_updates`](../../scripts/webui/updates/build_updates.py) owns the
matching rules).

## Primary generated outputs

Animator FBX resource snapshots include both loose files and rows in
`game/Unity.sqlite` under the same logical `Unity/Animator/<name>` identity.
Moving a model into the store is not a deletion. Loose files take precedence
when both representations exist. Exact comparisons and PathID relocation
checks normalize FBX export metadata with the maintained format reader, so
SDK timestamps and generated identifiers do not become content changes.

Wwise `unknown/<numeric-id>.flac` copies may disappear after classification
while a classified Wwise copy of `<numeric-id>.flac` survives. Suppress that
copy's add/delete churn only when both files have the exact same nonzero
FLAC STREAMINFO PCM identity; a name or media ID alone is insufficient.
This check includes classified copies already present in the previous export.

`webui/data/updates/latest.json` and
`webui/data/updates/{characters,story,map,gameplay}.json`.

`page_records.py` compares the same export-only source projection on both
sides: Story table conversations and available cutscene object documents;
Map level definitions, per-level registry rows and authored level/config/script
files; Gameplay primary rows and explicit field-to-table ownership joins
(`gameplay_sources.py`), plus literal serialized-file paths in admitted rows;
Gameplay item catalog joins from raw item, recipe,
building, shop, cost and achievement rows. Gameplay items reuse their catalog builder
on both exports, retaining grouped medal identities, each original tier's source,
and matching limited-item records with their explicit `LTItemTable` mapping.
It compares direct displayed relationships without recursively following
the entire recipe network. String/key equality alone never creates a Gameplay
table link. A character owns its growth, skills, potentials and factory talents,
not recommended weapons or the production network of a required material.
Default-weapon and cost-item labels are terminal projections. Set definitions
do not acquire sibling equipment rows, and an enemy template reference does
not acquire another EnemyTable variant. Shared definitions still affect every
explicit owner. Item usage receipts honor their declared `field` selection,
merging multiple selections without widening to the whole referenced row;
related ingredient labels and machine footprints do not crawl their catalogs.
SNS options join only through `dialogContentData.*.dialogOptionIds`, never an
arbitrary string in the conversation. Numeric values and I18nText wrappers
cannot create untyped links either.
Equipment selects the same explicit `equipList` membership and formula outcome
as the Gameplay builder, including its last-match selection. The set's `list`
effect definitions belong to its members; the surrounding `equipList` is only
a selector, so adding a sibling does not change existing equipment. Regional
name/storage labels, formula-pack names and unlock-channel names are terminal
projections; regional development levels, map capacity, shop inventories and
pack configuration never become equipment updates. Recipe chains remain shared
by their actual recipe owners, with cost-item labels kept terminal.
Gameplay's `gem:<groupId>` comparison owns WorldEnergyPointGroupTable rows and
uses the same pool, reciprocal stage and unambiguous region joins as the Gem
page. Selected term/level/region labels are terminal; compatible weapon stats
are not acquired as point updates. The group catalog must exist on both sides,
so a missing prior export family is not treated as every point being new.
Combat stages use `stage:<DungeonTable key>` in the Gameplay sidecar. Only the
supported combat categories participate. The stage owns its Dungeon/Raid rows,
selected series/type labels, field description, rewards, displayed enemy
modifiers/Buff references, and exact activity-navigation slots. Sibling dungeon
configurations and series membership lists are excluded. This source comparison
does not authenticate runtime waves or promote stale recovered battle evidence.
Activities schema 3 retains individual supporting-table identities and expands
each `ActivityTable/<id>` identity with the page's exact related-reward slots
and maintained guide references, including schedule, tag labels, conditions,
tasks, supply submissions and rewards. Related item/dungeon/parent-activity
labels remain terminal. Both subpages expose list/title badges, field details
and the shared Version changes filter; absent comparisons clear that filter.
The shared file collector and decorator also honor `data-update-files-exclude`.
Gameplay loadout candidate lists carry it; their selected summary previews do
not. Closed controls still have DOM images, so scanning every descendant image
without this ownership boundary incorrectly reports the entire equipment catalog
as the selected character's resource changes. Ordinary collapsed owner details
remain eligible; visual collapse alone is not an ownership rule.
Linked serialized files use canonical export-relative paths, so the same file
comparison contract applies as on Map. Linked localization uses only common languages.
These badges report authored-source changes, not final recovery parity or
runtime behavior. Missing primary catalogs publish an unavailable sidecar;
missing optional tables are excluded on both sides. Gameplay compares each
kind whose primary table exists on both sides and reports unavailable kinds
in `skippedKinds`; this does not suppress changes in the other kinds. Entries are uncapped and
independent of media flags. Deleted IDs are retained as comparison data,
without inserting old content into current page datasets.
Story/Map/Gameplay sidecar schema 3 adds field-level `changes` and a bounded
`file` comparison for changed linked export files; Characters schema 4 includes
catalog field changes. One-sided records retain field paths so the frontend
can select a common data language. Comparison values serialize integers beyond
JavaScript's safe range as exact decimal strings, including nested values,
so text-handle IDs retain their precision. Linked file comparisons reuse the feed's
maintained readers and preview limits, including coverage and truncation notes.
The normal detail panels expose old/current values without enabling debug;
grouped Map variants retain their source owners instead of overwriting a
sibling variant's change. Enemy detail comparisons are separated by exact
configuration owner, matching the IDs and badges on the variant selectors; a
shared-source change can appear under each affected owner. Status-only legacy sidecars retain their badges with
an explicit missing-detail explanation.
Page controls, the decoded-diff panel, and the client-side waveform view are in
the header comment of `webui/src/features/updates/index.js`.

## Evidence boundary

- The default feed covers WebUI-facing exported JSON plus exported image,
  model, video, and decoded audio assets. `--no-audio` omits decoded audio
  only; `--text-only` omits all assets; `--full-export-scan` is a broad audit,
  not the normal feed.
- A recognized relocation proves export identity under its recorded matching
  rule; it does not prove that the underlying game event or semantic owner is
  unchanged.
- A decoded diff proves only what its reader covers. A whole-file reader bounds
  the change exactly; a bounded reader does not, and a change it cannot see is
  reported rather than hidden. The rendering is evidence about the payload,
  never a file the game ships.
- The audio waveform comparison is a listening aid, not evidence of semantic
  event changes.
- Both complete roots are mandatory. There is no first-run installed-VFS mode.
- Map file families and Gameplay serialized-file families participate only
  when present in both exports. The Map sidecar records compared and skipped
  families; grouped navigation highlights changes in any physical variant.
- The Characters sidecar fails closed: missing, invalid, empty, or legacy
  exports publish an unavailable sidecar rather than treating the roster as new,
  and only languages present on both sides participate. Asset flags do not
  disable it.
- Pruning old duplicate files is destructive: preview first and never target
  the current export or repository root.

## Focused refresh commands

```bat
.\build_updates.bat OLD NEW
.\build_updates.bat OLD NEW --no-audio
.\build_updates.bat OLD NEW --exact
python -m scripts.webui.updates.build_updates --refresh-previous-export-baseline
```

## Highest-value remaining gaps

- Keep focused roots synchronized with actual WebUI consumers.
- Preserve deterministic categories when exported layouts evolve.
- Keep pruning guards fail-closed and independently tested.
- LevelScriptData is the largest changed family and its reader is bounded, so
  most of its entries report an identical decoded view. Widening that reader is
  what turns those rows into real diffs.
