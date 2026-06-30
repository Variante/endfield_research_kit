# Texture2D Output Collision Status - 2026-06-30

## Scope

Follow-up after the Animator recovery pass. The remaining Texture2D issue was not
an AnimeStudio Warning/Error log family; it was the wrapper asset-status state:
`convert_by_type_Texture2D.json` reported `uncertain_output_collision` dirty
source groups even though every matched Texture2D entry had an output.

Inputs inspected:

```text
export_full/recovered/AnimeStudio-cli/StreamingAssets/asset_status/convert_by_type_Texture2D.json
export_full/recovered/AnimeStudio-cli/Persistent/asset_status/convert_by_type_Texture2D.json
export_full/recovered/AnimeStudio-cli/*/convert_by_type/Texture2D
reports/export_full_summary.json
```

## Original Status

Before this pass, the Texture2D status manifests showed no missing output and no
export errors, but all duplicate output paths were classified as uncertain raw
hash collisions.

| root | matched entries | source groups | clean groups | dirty groups | output entries | actual files | missing outputs | collision paths | uncertain entries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `StreamingAssets` | 126,496 | 104,222 | 103,975 | 247 | 126,496 | 126,226 | 0 | 6 | 276 |
| `Persistent` | 5,960 | 1,172 | 1,089 | 83 | 5,960 | 5,877 | 0 | 3 | 86 |

The collision output paths were:

```text
Background_p59E0F9C8D2F90F4C.png
InputFieldBackground_pFF9E60FF3ED20F4C.png
Knob_pA35E39E3A5CB0F4C.png
T_wpn_sword_0009_01_D_p666E9D8C5CA0F2E9.png
UIMask_p968E5260DA470F4C.png
UISprite_p39CC623422330F4C.png
```

## Cause

Converted Texture2D files are named by exported asset identity:

```text
FixFileName(Name)_p<PathID>.png
```

Endfield repeats some small UI Texture2D objects across many AB source
identities. The repeated rows have the same `Type`, `Name`, and `PathID`, but
different source paths, offsets, containers, and raw serialized-object hashes.
The wrapper previously treated same `Type + Name + PathID` with differing raw
`Hash` values as `raw_hash_output_collision`, which made those groups dirty.

That was too pessimistic for Texture2D output validation. `AssetEntry.Hash` is
`Object.GetHash()` over the raw serialized Unity object. It can differ for rows
that decode to the same PNG bytes. For this status check, the exported file is
the decoded image, so the decisive question is whether the individual source
rows decode to the same PNG.

## Verification

A temporary exact-export verification was run for every currently colliding
Texture2D row.

Temporary inputs/outputs:

```text
tmp/texture2d_collision_verify/rows.json
tmp/texture2d_collision_verify/all_rows_exact_results.json
tmp/texture2d_collision_verify/all_rows_exact_summary.json
```

Each row was exported into its own temp directory using an exact `filter_data`
selector plus a deliberately non-matching `--names a^` filter so `filter_data`
was the only selector:

```bat
AnimeStudio.CLI.exe <source_root> <tmp_row_output> ^
  --game ArknightsEndfield --logger_flags Warning Error ^
  --group_assets ByType --map_op None ^
  --export_type Convert --types Texture2D:Both ^
  --names a^ --filter_data <row_filter.json>
```

Verification result:

| output path | rows checked | unique decoded PNG hashes | matched current exported PNG |
| --- | ---: | ---: | --- |
| `Background_p59E0F9C8D2F90F4C.png` | 203 | 1 | yes |
| `InputFieldBackground_pFF9E60FF3ED20F4C.png` | 2 | 1 | yes |
| `Knob_pA35E39E3A5CB0F4C.png` | 8 | 1 | yes |
| `T_wpn_sword_0009_01_D_p666E9D8C5CA0F2E9.png` | 2 | 1 | yes |
| `UIMask_p968E5260DA470F4C.png` | 17 | 1 | yes |
| `UISprite_p39CC623422330F4C.png` | 130 | 1 | yes |

All 362 colliding rows were processed. There were zero subprocess failures,
zero stdout/stderr warnings, and every exact row export produced exactly one
PNG whose SHA-256 matched the current shared output file.

## Implemented

`scripts/export_full_from_game.py` now distinguishes this case as:

```text
same_asset_id_output_reference
```

Meaning: multiple source identities point at the same exported asset identity
(`Type`, `PathID`, `Name`) and therefore the same output path. This category is
kept in the status manifest, but it is no longer treated as an uncertain output
collision.

This is not a blanket suppression of raw-hash mismatches for every type. The new
classification is limited to Texture2D collision groups where the exported asset
identity is identical apart from the raw serialized-object hash.

## Refreshed Status

Report-only refresh command:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index ^
  --animestudio-scope assets --animestudio-asset-mode full ^
  --animestudio-stages convert_by_type --animestudio-asset-types Texture2D ^
  --report-only
```

Run id:

```text
reports/20260629_224707
```

Final refreshed status:

| root | matched entries | source groups | clean groups | dirty groups | output entries | actual files | missing outputs | same-asset reference paths | same-asset reference entries | uncertain collisions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `StreamingAssets` | 126,496 | 104,222 | 104,222 | 0 | 126,496 | 126,226 | 0 | 6 | 276 | 0 |
| `Persistent` | 5,960 | 1,172 | 1,172 | 0 | 5,960 | 5,877 | 0 | 3 | 86 | 0 |

The six `.png.empty.json` marker files per source remain classified as marker
outputs for zero-size font placeholder textures, not decode failures.

## Conclusion

The current Texture2D collision family is understood.

- There are no missing Texture2D outputs.
- There are no Texture2D warning/error logs in retained evidence.
- All currently colliding rows decode to byte-identical PNG files.
- Status manifests keep the collision evidence under
  `same_asset_id_output_reference_*` fields.
- Texture2D dirty source groups are now zero for both source roots.