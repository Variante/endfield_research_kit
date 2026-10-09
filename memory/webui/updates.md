# Updates page recovery

## Purpose

Updates reports exported game-data changes between one saved previous export
and one current complete export. It must never report repository documentation,
WebUI source edits, generated reports, or scratch data as game updates.

## Inputs and recovery flow

`export.bat --changed-only` automates this comparison after synchronizing all
supported installed-game inputs and building the pages. It uses exact content
hashes and its own cache under `reports/export/sync/`, leaving the manual
comparison cache independent. The first run adopts a coherent current export
as its old side; if the current export is partial or mixed, it uses the complete
export named by `--previous-export-root` or `ENDFIELD_PREVIOUS_EXPORT_ROOT`.
Without either, it initializes a baseline and emits no invented all-added feed.
Subsequent comparisons use the last successful synchronization, never an
intermediate failed export. Unchanged installed inputs keep the last feed.

An adopted legacy export can cover fewer data families than the current
all-page synchronization. Its first feed then includes export-coverage changes
as well as game-content changes; do not attribute every added row to a client
update without matching recorded coverage. Subsequent automatic snapshots use
the same all-page scope.

The orchestrator stages the feed and all sidecars together, then publishes the
directory and records the new complete snapshot only after all stages succeed.
Managed snapshots retain the last comparison's old side and the next baseline;
they never delete the user-supplied old export. Snapshot storage and extraction
ownership are documented in [the extraction pipeline](../game_data/extraction_pipeline.md).

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
5. Compare linked authored Story, Gameplay, Map and Production source records with the
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

`webui/data/updates/latest.json` and
`webui/data/updates/{characters,story,map,gameplay,production}.json`.

`page_records.py` compares the same export-only source projection on both
sides: Story table conversations and available cutscene object documents;
Map level definitions, per-level registry rows and authored level/config/script
files; Gameplay primary rows and their exact string references to related
tables and serialized files; Production catalog joins from raw item, recipe,
building, shop, cost and achievement rows. Production reuses its catalog builder
on both exports, retaining grouped medal identities, each original tier's source,
and matching limited-item records with their explicit `LTItemTable` mapping.
It compares direct displayed relationships without recursively following
the entire recipe network. Numeric strings and I18nText wrappers do not
create Gameplay table links: skill description values must not resolve to
item-type catalogs and pull unrelated characters into an entry's comparison.
Linked serialized files use canonical export-relative paths, so the same file
comparison contract applies as on Map. Linked localization uses only common languages.
These badges report authored-source changes, not final recovery parity or
runtime behavior. Missing primary catalogs publish an unavailable sidecar;
missing optional tables are excluded on both sides. Gameplay compares each
kind whose primary table exists on both sides and reports unavailable kinds
in `skippedKinds`; this does not suppress changes in the other kinds. Entries are uncapped and
independent of media flags. Deleted IDs are retained as comparison data,
without inserting old content into current page datasets.
Story/Map/Gameplay/Production sidecar schema 3 adds field-level `changes` and a bounded
`file` comparison for changed linked export files; Characters schema 4 includes
catalog field changes. One-sided records retain field paths so the frontend
can select a common data language. Comparison values serialize integers beyond
JavaScript's safe range as exact decimal strings, including nested values,
so text-handle IDs retain their precision. Linked file comparisons reuse the feed's
maintained readers and preview limits, including coverage and truncation notes.
The normal detail panels expose old/current values without enabling debug;
grouped Map variants retain their source owners instead of overwriting a
sibling variant's change. Status-only legacy sidecars retain their badges with
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
