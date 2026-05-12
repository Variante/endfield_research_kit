# Game-update playbook

What to do when Endfield updates and you want the WebUI recovery to keep
working. Read this before reaching for any of the IL2CPP tools.

This document is the operational follow-up to
[dialog_id_registry.md](dialog_id_registry.md). Read that if you want the
"why"; this file is the "how".

## TL;DR (the 95% case)

Most game updates are just data changes. Recovery handles them
automatically:

```
.\export.bat
```

That's it. The pipeline re-extracts the new game data, rebuilds
`DialogIdTable` registry, regenerates every conv JSON, refreshes
warnings. **No tool in this playbook needs the game running.**

Then, if a local IL2CPP metadata artifact exists, run the separate metadata
catalog canary. `export.bat` does not generate this file.

```
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --cache-metadata
```

If this is the first run for the current recovered metadata cache, the report
becomes the baseline. On later game updates, inspect:

```
reports/option_flow_runtime_metadata_diff.md
```

No focus-type or body-target drift: business as usual.

Drift: jump to "When the metadata catalog changes" below.

## What "export.bat" does and why nothing else is usually needed

Order of operations:

1. `scripts/export_full_from_game.py --skip-raw-vfs --skip-source-inventory`
   re-extracts every structured table and asset from the install at
   `D:\Program Files\Endfield Game\Endfield_Data\`. The game does NOT
   need to be running. If the game is open, close it first -- some
   files may be locked.
2. `scripts/recover_dialog_id_registry.py --quiet` re-builds
   `export_full/recovered/dialog_id_table_index.json` from the freshly-
   extracted `DialogIdTable.json`. This is the file
   `scene_order_gap_shared.py` reads to decide whether each scene is
   runtime-registered or unregistered (cut content).
3. `scripts/webui/build_updates.py` rebuilds the per-asset update feed.
4. `scripts/webui/build_story.py --languages CN --default-language CN`
   regenerates every conv JSON and embeds the right warnings. Every
   scene gets re-classified against the new registry.
5. `scripts/webui/build_assets.py` rebuilds the asset index.

After this, the WebUI is consistent with the new game version. Open the
WebUI at `python serve.py` and spot-check.

## What the metadata catalog contributes

`global-metadata.dat` does not contain authored story order by itself. It does
help the recovery in three narrower ways:

1. It confirms the runtime shape of dialog, timeline, trunk, and option
   classes after a game update.
2. It rules out false leads. The May 2026 catalog proved that
   `DialogTimelineOptionData` only has `optionIndex`, `changeFinishNum`, and
   `targetFinishNum`; the unresolved option target is not a hidden fourth
   serialized field there.
3. It names the exact method-body targets worth decoding next, such as
   `DialogTimelineManager._SelectIndexInTimeline`,
   `TryTriggerTrunkBindingOption`, `SetDialogOption`,
   `DialogOptionBehaviour.InitDialogOptions`, and DialogTree
   `GetNextIndex` / `SelectIndex`.

This is why the catalog is useful evidence, but it is still out-of-band from
the normal WebUI export.

## Recovering `global-metadata.dat`

The WebUI data exporters cannot reconstruct `global-metadata.dat` from
structured tables, VFS assets, or `GameAssembly.dll` alone. Treat it as a
separate local artifact.

Preferred recovery flow:

```
python tools\endfield-il2cpp\catalog_option_flow_metadata.py ^
  --metadata "D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat" ^
  --cache-metadata
```

The script validates the IL2CPP metadata magic/version, writes a cache to
`export_full/recovered/il2cpp/global-metadata.dat`, and records provenance in
`export_full/recovered/il2cpp/global-metadata_source.json`. Future catalog
runs prefer that cache before checking the local install path. Future
`--cache-metadata` runs prefer the install path so a game update refreshes the
cache instead of reusing the old copy.

If the installed game no longer has a metadata file, use a clean copy from a
previous cache or patch package and pass it via `--metadata`. If no valid
metadata artifact exists, continue with `export.bat`; only the metadata drift
canary is unavailable.

## When the metadata catalog changes

1. Re-run a compact focus report:

   ```
   python tools\endfield-il2cpp\catalog_option_flow_metadata.py --only-focus
   ```

2. Inspect these files in this order:

   - `reports/option_flow_runtime_metadata_diff.md`: first stop after an
     update. If it says no drift, the runtime option-flow shape probably did
     not move.
   - `reports/option_flow_runtime_metadata_focus_diff.md`: compact view of the
     exact classes the WebUI recovery cares about.
   - `reports/option_flow_runtime_metadata_focus.md`: current field/method
     shape for the focus classes.
   - `reports/option_flow_runtime_metadata.md`: full vocabulary search when a
     new class or method name appears.

3. In those reports, look for:

   - `metadata` version, size, and sha256 changes. A hash-only change with no
     focus/body-target drift is usually harmless.
   - focus type field changes on `DialogTimelineOptionData`,
     `DialogOptionPlayableAsset`, `DialogOptionBehaviour`,
     `DialogTrunkBehaviour`, `DialogTimelineManager`,
     `DialogTreeOptionNode`, and `DialogTreeExOptionNode`.
   - `bodyTargets` additions/removals around
     `_SelectIndexInTimeline`, `TryTriggerTrunkBindingOption`,
     `SetDialogOption`, `ResetDialogOption`, `OnJumpForward`,
     DialogTree `GetNextIndex`, and `SelectIndex`.
   - new names containing `target`, `next`, `branch`, `route`, `jump`,
     `logic`, `condition`, `finish`, or `select`.

4. Recovery interpretation:

   - A new serialized field on a focus option/tree/timeline type is the best
     candidate for new WebUI recovery evidence.
   - A new method-body target is a pointer for the next targeted backend audit;
     do not promote a new route rule from the name alone.
   - Removed or renamed focus types usually mean docs/comments need refreshing
     unless the structured exports also start failing.
   - If `DialogTimelineOptionData` still only has `optionIndex`,
     `changeFinishNum`, and `targetFinishNum`, keep treating unresolved option
     target recovery as a Timeline/runtime method problem, not a missing field
     on that data object.

The older live-process dump and decompiler path is retired from this active
playbook. Keep future work focused on offline metadata, structured exports,
AnimeStudio decoded assets, and targeted backend audits unless a very specific
method-body question justifies a new tool.

## When the registry is wrong shape

Symptoms: `recover_dialog_id_registry.py --quiet` runs but reports
near-zero entries; many scenes that should be registered come back as
`unregisteredScene`.

Likely cause: the game changed `DialogIdTable.json`'s binary format
(e.g. now encrypted at rest, or now uses numeric IDs instead of string
keys).

Triage:

1. Run the recovery without `--quiet` and inspect the count:
   ```
   python scripts\recover_dialog_id_registry.py
   ```
   Compare to the May 2026 baseline (~4 500 entries). A drop to 0-100
   means the extractor's regex isn't finding identifiers.

2. Inspect the raw bytes:
   ```powershell
   Format-Hex `
     -Path "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\..." `
     -Count 256
   ```
   (Adjust the path -- `export_full_from_game.py` writes a copy under
   `export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json`
   which is the actual input.)

3. If you can still see ASCII `dlg_*` strings: the regex in
   `scripts/recover_dialog_id_registry.py` needs widening. If you
   can't see them: the table is now encrypted / serialized
   differently, and you need to identify how the runtime decodes it. Use
   `global-metadata.dat` to find the `DialogIdTable`-related methods first;
   only add a new backend audit or decompilation tool when that metadata gives
   a concrete target.

## Quick reference

| When | Run | Game running? |
| ---- | --- | ------------- |
| Normal post-update refresh | `.\export.bat` | No (close it) |
| Cache/catalog IL2CPP metadata | `tools\endfield-il2cpp\catalog_option_flow_metadata.py --cache-metadata` | No |
| Focus option-flow drift | `tools\endfield-il2cpp\catalog_option_flow_metadata.py --only-focus` | No |
| Sanity-check the registry | `scripts\recover_dialog_id_registry.py` (no --quiet) | No |
| New IL2CPP investigation | Add a targeted offline audit from catalog evidence | No |
