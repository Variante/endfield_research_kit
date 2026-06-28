# AnimeStudio AB Understanding Report

Generated from the current checkout evidence on 2026-06-28.

## Evidence Used

- Summary: `reports/export_full_summary.json`
- Report run: `20260627_215637`
- Report run root: `reports/20260627_215637`
- VFS indexes:
  - `export_full/recovered/AnimeStudio-cli/StreamingAssets/vfs_index/bundle_vfs_index.json`
  - `export_full/recovered/AnimeStudio-cli/Persistent/vfs_index/bundle_vfs_index.json`
- AnimeStudio asset maps:
  - `export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json`
  - `export_full/recovered/AnimeStudio-cli/Persistent/maps/endfield_persistent_assets.json`

## Scope

This report counts existing AB files from the current VFS `Bundle` block indexes.
Those indexes cover block `Bundle` / `7064D8E2` only. They do not count
`InitialBundle` / `0CE8FA57` as AB files, although the AnimeStudio asset maps do
contain objects sourced from `InitialBundle`.

Definition used here:

- **VFS-understood** means the bundle entry is present in the VFS index with no
  missing block or missing chunk.
- **AnimeStudio fully understood** would mean the AB file can be certified from
  existing evidence as processed by AnimeStudio without warnings or errors.
- **Not certifiable clean** means existing logs do not prove the AB was processed
  warning-free. This is not the same as a proven broken AB.

## Executive Answer

The current VFS indexes contain **518,131** `Bundle` AB entries:

| Source | Bundle AB entries | Bundle bytes | Missing chunks |
| --- | ---: | ---: | ---: |
| `StreamingAssets` | 257,434 | 33,313,467,140 | 0 |
| `Persistent` | 260,697 | 33,599,451,919 | 0 |
| **Total** | **518,131** | **66,912,919,059** | **0** |

At the VFS container level, the current indexed `Bundle` AB population is clean:
all indexed chunks exist and there are no missing chunks.

At the AnimeStudio understanding level, the existing evidence cannot certify any
individual AB as fully warning-free. The run has source-level and object-level
warnings/errors, but the logs do not consistently include the source AB path for
each warning. Therefore:

| Question | Count |
| --- | ---: |
| VFS-indexed `Bundle` AB entries | 518,131 |
| ABs proven present at VFS layer | 518,131 |
| ABs exactly proven warning-free by current AnimeStudio logs | 0 |
| ABs not certifiable clean from existing evidence | 518,131 |
| ABs exactly proven dirty by source AB path | Not available from current logs |

The strict answer to "how many could not be fully understood" is therefore:

**518,131 are not certifiable as fully understood from the existing evidence.**

That is a conservative evidence statement. It does not mean every one of those
ABs is actually broken; it means the current logs do not provide a per-AB clean
certificate, and the run is not globally warning-free.

## AnimeStudio Evidence

The broad AnimeStudio debug export did not complete warning-free.

| Source | Stage | Return code | Output files | Warnings | Errors | Export errors | Exceptions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `StreamingAssets` | `maps` | 0 | 2 | 1 | 0 | 0 | 0 |
| `StreamingAssets` | `convert_by_type` | 1 | 315,354 | 1 | 283 | 283 | 0 |
| `StreamingAssets` | `json_by_type` | 0 | 1,107,091 | 11,948 | 0 | 0 | 11,948 |
| `Persistent` | `maps` | 0 | 2 | 0 | 0 | 0 | 0 |
| `Persistent` | `convert_by_type` | 1 | 16,156 | 0 | 221 | 221 | 0 |
| `Persistent` | `json_by_type` | 0 | 105,072 | 1,486 | 0 | 0 | 1,486 |
| **Total** |  |  | **1,543,677** | **13,436** | **504** | **504** | **13,434** |

Important details:

- `maps` found one unknown class ID in `StreamingAssets`.
- `convert_by_type` returned `1` for both sources.
- `json_by_type` returned `0` for both sources, but logged 13,434 partial
  MonoBehaviour decode warnings.
- `metadata_only_json_count` is `0` in both JSON stages, so the JSON issue is
  partial MonoBehaviour recovery rather than complete metadata-only fallback.

## Conversion Coverage

The conversion stage selected five asset types for cache/output accounting:
`Texture2D`, `Shader`, `Mesh`, `Sprite`, and `AnimationClip`.

| Source | Matched conversion entries | Output entries | Missing outputs | Allowed missing | Unexpected missing | Export errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `StreamingAssets` | 324,820 | 297,357 | 27,463 | 6,144 | 21,319 | 283 |
| `Persistent` | 20,260 | 14,422 | 5,838 | 8 | 5,830 | 221 |
| **Total** | **345,080** | **311,779** | **33,301** | **6,152** | **27,149** | **504** |

By type:

| Source | Type | Matched | Output | Missing | Allowed missing | Export errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `StreamingAssets` | `Texture2D` | 126,496 | 126,402 | 94 | 0 | 0 |
| `StreamingAssets` | `Shader` | 271 | 30 | 241 | 0 | 241 |
| `StreamingAssets` | `Mesh` | 59,287 | 53,143 | 6,144 | 6,144 | 0 |
| `StreamingAssets` | `Sprite` | 20,917 | 0 | 20,917 | 0 | 0 |
| `StreamingAssets` | `AnimationClip` | 117,849 | 117,782 | 67 | 0 | 42 |
| `Persistent` | `Texture2D` | 5,960 | 5,954 | 6 | 0 | 0 |
| `Persistent` | `Shader` | 222 | 9 | 213 | 0 | 213 |
| `Persistent` | `Mesh` | 491 | 483 | 8 | 8 | 0 |
| `Persistent` | `Sprite` | 5,603 | 0 | 5,603 | 0 | 0 |
| `Persistent` | `AnimationClip` | 7,984 | 7,976 | 8 | 0 | 8 |

The most concrete parser/exporter gaps in this run are shader export and some
animation export. Sprite conversion also produced no outputs in this accounting,
but the summary does not classify those as `Export ... error` lines.

## Asset Map Coverage

The AnimeStudio asset maps contain:

| Source | Asset map entries | From `Bundle` block | From `InitialBundle` block |
| --- | ---: | ---: | ---: |
| `StreamingAssets` | 1,400,954 | 1,395,280 | 5,674 |
| `Persistent` | 127,902 | 122,228 | 5,674 |
| **Total** | **1,528,856** | **1,517,508** | **11,348** |

This shows AnimeStudio enumerated many Unity objects from `Bundle` ABs, and also
objects from `InitialBundle`. It still does not prove every AB was fully
understood, because object enumeration is weaker than warning-free conversion
and JSON decoding.

## Why Exact Per-AB Dirty Counts Are Not Available

Current logs are sufficient for stage-level and object-level counts, but not for
exact AB-level classification:

- `Export <Type>:<Name> error` lines identify asset type/name but not the source
  AB path, source offset, or PathID.
- Many asset names are not unique across ABs, so matching errors back by
  type/name would overcount or undercount.
- Partial MonoBehaviour warnings identify object numbers and offsets, but not
  the source AB file.
- The current summary does not write a per-AB clean/dirty manifest.
- The current VFS index only covers `Bundle`; if the desired population includes
  `InitialBundle`, a matching VFS index for `InitialBundle` is needed too.

## Recommended Next Step

To answer the stronger question exactly, change the AnimeStudio wrapper/logging
or post-processing to emit a per-source-file status manifest with:

- source VFS block type and chunk path
- AB VFS name, offset, length, and data hash
- object counts by ClassIDType
- warning count and error count per AB
- conversion outputs and missing outputs per AB
- partial MonoBehaviour and metadata-only JSON counts per AB

Then the exact report can separate:

- fully clean ABs
- ABs with only unsupported/non-exported object types
- ABs with partial MonoBehaviour recovery
- ABs with conversion/export errors
- ABs that were indexed but never loaded by AnimeStudio


