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
3. Scan the same focused text and asset roots on both sides. Asset changes use
   fast size fingerprints by default; `--exact` hashes contents.
4. Compare stable `CharacterTable` rows and their referenced localized names
   as a Characters-page sidecar, without feeding those results back into
   character recovery or grouping.
5. Publish `webui/data/updates/latest.json` and
   `webui/data/updates/characters.json`; scanner cache and history remain under
   `.game-data-tracker/`.

Path identity is supplemented by two fail-closed relocation joins. Unity
exports with generated `_p<PathID>` suffixes are paired only when their stable
kind, extension, and suffix-stripped path are one-to-one. Unmatched decoded
audio is paired only when equal-size candidates have byte-identical content;
then unmatched FLAC candidates are compared by their STREAMINFO format, sample
count, and decoded-PCM MD5 so lossless re-encodes and metadata changes can be
recognized. Same-name pairs take precedence, and a content-only or PCM-only
pair must be unique unless an unchanged parent folder makes each duplicate
one-to-one. The exact-content lane already fixes size; STREAMINFO fixes format,
sample count, duration, and decoded PCM. Pairs with unchanged effective content
are omitted as path-only churn. A stable Unity identity with changed bytes
remains one `modified` entry with both paths and an explicit match method.
Multiple candidates in the same folder remain `added` plus `deleted`.

The post-pass also suppresses an obsolete numeric `wwise/unknown` AudioDialog
copy when its filename is the exact 64-bit FNV-1 external-source identity of one
current authored dialog path, the authored basename resolves to exactly one
canonical voice asset, identical bytes are verified, and that canonical asset
exists in both exports. This records duplicate cleanup, not a deletion. A
repeated basename, missing peer, hash ambiguity, or byte mismatch fails closed
to the original add/delete result.

Modified decoded audio is compared in the browser from the existing old/new
asset URLs. The detail view plots both amplitude envelopes on a shared absolute
timeline and a third envelope-delta lane, so duration changes, silence shifts,
and broad loudness edits are visible without adding derived waveform data to
the feed. This is a listening aid, not evidence of semantic event changes.

Size sorting uses the absolute applicable magnitude: new file size for an
addition, old file size for a deletion, and absolute size delta for a
modification. This keeps add/delete rows meaningful in the same sort mode.

## Evidence boundary

- The default feed covers WebUI-facing exported JSON plus exported image,
  model, video, and decoded audio assets.
- `--no-audio` omits decoded audio only. `--text-only` omits all assets.
- `--full-export-scan` is a broad audit, not the normal WebUI feed.
- A recognized relocation proves export identity under its recorded matching
  rule; it does not prove that the underlying game event or semantic owner is
  unchanged.
- Both complete roots are mandatory. There is no first-run installed-VFS mode.
- Character tags fail closed when either `CharacterTable` is missing or
  invalid, including invalid overlays and tables without valid character rows;
  asset flags do not disable this text-derived comparison. Localization changes
  are compared only for languages with valid tables on both sides, with other
  languages reported as degraded rather than inferred as roster changes.
- Pruning old duplicate files is destructive: preview first and never target
  the current export or repository root.

## Focused refresh

```bat
.\build_updates.bat OLD NEW
.\build_updates.bat OLD NEW --no-audio
.\build_updates.bat OLD NEW --exact
python -m scripts.webui.updates.build_updates --refresh-previous-export-baseline
```

## Remaining gaps

- Keep focused roots synchronized with actual WebUI consumers.
- Preserve deterministic categories when exported layouts evolve.
- Keep pruning guards fail-closed and independently tested.
