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

## Evidence boundary

- The default feed covers WebUI-facing exported JSON plus exported image,
  model, video, and decoded audio assets.
- `--no-audio` omits decoded audio only. `--text-only` omits all assets.
- `--full-export-scan` is a broad audit, not the normal WebUI feed.
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
python scripts\build_updates.py --refresh-previous-export-baseline
```

## Remaining gaps

- Keep focused roots synchronized with actual WebUI consumers.
- Preserve deterministic categories when exported layouts evolve.
- Keep pruning guards fail-closed and independently tested.
