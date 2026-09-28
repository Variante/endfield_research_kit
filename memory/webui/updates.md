# Updates page recovery

## Purpose

Updates reports exported game-data changes between one saved previous export
and one current complete export. It must never report repository documentation,
WebUI source edits, generated reports, or scratch data as game updates.

## Inputs and recovery flow

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
5. Publish the feed; scanner cache and history remain under
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

`webui/data/updates/latest.json` and `webui/data/updates/characters.json`.
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
