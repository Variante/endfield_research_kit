# AnimeStudio Texture2D Format Recovery

Date: 2026-06-28

## Scope

This pass investigated `Texture2D:Both` rows reported as silent no-output cases,
especially rows that logged:

```text
Nothing exported. 1 assets skipped (not extractable or files already exist)
```

The goal was to distinguish real Texture2D parser/decoder failures from missing
stream data, zero-sized Unity placeholder textures, and export filtering or
accounting mismatches. No wrapper code was changed.

## Findings

Current missing-output rows from the existing Texture2D filter shards classify
as:

| Class | Unique rows | Cause |
| --- | ---: | --- |
| Zero-size placeholder Texture2D | 12 | Real Unity `Texture2D` objects named `Font Texture` with width `0`, height `0`, image bytes `0`, stream-data size `0`, and empty stream path. These are correctly non-extractable; there is no pixel payload to decode. |
| Asset-map name mismatch, parseable image | 88 | Filter/map row `Name` does not match the actual Unity `Texture2D.m_Name` for the same PathID. The texture object parses correctly and has valid image bytes, but a `--names` filter built from the map row name prevents export. |

The non-font misses are not unsupported image formats and not missing `.resS`
stream data. Exporting the same source offsets without the map-name filter
loaded the target PathIDs and produced valid metadata. Representative actual
textures include:

| Map row name | Actual Texture2D name | Format | Size | Stream bytes |
| --- | --- | --- | --- | ---: |
| `dlgtl_c13m2_9_sub_1__1` | `Terrain_6_55_16_N` | `DXT5` | 132x132 | 17,424 |
| `b7509587b7b3ec9f` | `T_auto_generated_HLOD0_map01_lv006_art_-1957205189_N` | `BC7` | 1024x1024 | 1,398,128 |
| `assets/.../s_mod_map02_railing+1_001_01_col1_um01.fbx` | `item_port_seedcol_1` | `BC7` | 256x256 | 65,536 |
| `assets/.../terrain_5_25_8_a.tga` | `remotecomm_image_e1m5_2` | `BC7` | 1600x900 | 1,440,000 |

Across all 88 parseable-but-filtered rows, observed formats were already covered
by the current decoder: `DXT5`, `BC7`, `RG16`, `RGBAHalf`, and `RGBA32`.

## Evidence

Minimal original missing sample:

```json
{
  "Source": "D:\\Program Files\\Endfield Game\\Endfield_Data\\StreamingAssets\\VFS\\0CE8FA57\\D937E67494E3B4C19C00B4CD263ED388.chk",
  "Offset": 7661199,
  "Name": "Font Texture",
  "PathID": -6603019454663767376,
  "Type": "Texture2D"
}
```

Targeted convert result:

```text
[Info] [0/1] Exporting Texture2D: Font Texture
[Info] Nothing exported. 1 assets skipped (not extractable or files already exist)
```

Targeted JSON for that same PathID:

```json
{
  "m_Width": 0,
  "m_Height": 0,
  "m_TextureFormat": "RGBA32",
  "image_data": { "Size": 0 },
  "m_StreamData": { "offset": 0, "size": 0, "path": "" },
  "m_Name": "Font Texture"
}
```

Positive control from the same chunk:

```json
{
  "Name": "T_default_mro_MRO",
  "PathID": -1246962829539794806,
  "m_Width": 4,
  "m_Height": 4,
  "m_TextureFormat": "DXT1",
  "image_data": { "Size": 8 },
  "m_StreamData": {
    "size": 8,
    "path": "archive:/CAB-d29c4e95cbb3b4d25d7f11ebc90d49ca/CAB-d29c4e95cbb3b4d25d7f11ebc90d49ca.resS"
  }
}
```

Full missing-row classification was generated under:

```text
tmp/animestudio_texture2d_format_probe/texture2d_missing_classification.json
```

## Verification

Commands run:

```bat
AnimeStudio.CLI.exe "<exact .chk>" tmp\animestudio_texture2d_format_probe\missing_convert_chunk --game ArknightsEndfield --logger_flags Info Warning Error --group_assets ByType --export_type Convert --names tmp\animestudio_missing_probe_20260628\texture_missing_names.txt --filter_data tmp\animestudio_missing_probe_20260628\texture_missing_filter.json --types Texture2D:Both
```

Result: reproduced the `Font Texture` silent skip.

```bat
AnimeStudio.CLI.exe "<exact .chk>" tmp\animestudio_texture2d_format_probe\positive_convert_chunk --game ArknightsEndfield --logger_flags Info Warning Error --group_assets ByType --export_type Convert --names tmp\animestudio_missing_probe_20260628\texture_existing_names.txt --filter_data tmp\animestudio_missing_probe_20260628\texture_existing_filter.json --types Texture2D:Both
```

Result: exported one PNG positive control.

```bat
AnimeStudio.CLI.exe "<representative .chk>" tmp\animestudio_texture2d_format_probe\representative_actual_convert\<label> --game ArknightsEndfield --logger_flags Info Warning Error --group_assets ByType --export_type Convert --names <actual-object-name>.txt --filter_data <representative-row>.json --types Texture2D:Both
```

Result: four representative non-font rows each exported one PNG when filtered
by the actual Unity object name instead of the asset-map row name.

## Conclusion

There is no Texture2D pixel decoder patch to make in this slice. The real
silent no-output `Font Texture` objects contain no dimensions and no image or
stream payload, so there is nothing to parse into an image. The other current
Texture2D missing rows are valid, parseable textures blocked by map-name based
filtering. The next fix should be in export selection/accounting: use
`filter_data` identity (`Source`, `Offset`, `PathID`, `Type`) to select assets,
or avoid treating asset-map `Name` as the output filename when it diverges from
`Texture2D.m_Name`.
## Follow-up Fix

Implemented after this investigation:

- `tools/AnimeStudio/AnimeStudio.CLI/Studio.cs` now treats `filter_data`
  identity as authoritative during final asset selection. A loaded asset whose
  source, bundle offset, PathID, and type match `filter_data` is kept even if
  the `--names` regex was built from a divergent asset-map display name.
- Ordinary name/container/type filters still apply when no `filter_data`
  identity matches.

Verification used a representative row from the
`asset_map_name_mismatch_parseable` class:

```text
map Name: 74618664eecd07dc
actual Texture2D.m_Name: facskill_hub_mine_spd_20
PathID: -598241958808313765
format: BC7
```

Running the CLI with the original wrong map-name `--names` file plus the
one-row `filter_data` now exports:

```text
tmp/texture2d_filter_identity_repro/after/Texture2D/facskill_hub_mine_spd_20_pF7B29E1BAB7F205B.png
```

This addresses the parseable missing-output class without changing Texture2D
decoding. The zero-size `Font Texture` placeholders remain correctly
non-extractable because they contain no pixel payload.