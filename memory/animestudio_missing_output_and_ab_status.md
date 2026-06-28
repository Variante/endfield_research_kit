# AnimeStudio Texture2D/Sprite Missing Output And AB Status

Date: 2026-06-28

## Scope

Worker slice covered `scripts/export_full_from_game.py` asset conversion cache/accounting and Texture2D/Sprite conversion behavior. No Shader, AnimationClip, or MonoBehaviour parser/exporter logic was changed.

## Findings

- `Sprite` missing outputs were a wrapper/export selection gap, not a Sprite converter exception. `Exporter.ExportSprite()` returns `false` when `Sprite.GetImage()` returns `null`; `Studio.ExportAssets()` only logs `Export ... error` for exceptions, so these show as missing outputs with `export_error_count=0`.
- `Sprite.GetImage()` needs the backing `Texture2D`, and can also resolve through `SpriteAtlas`. The existing sharded `Sprite:Both` calls parsed/exported Sprite only, so the referenced texture/atlas objects were not available. A targeted probe with the same Sprite filter wrote no output with `Sprite:Both`, then wrote the PNG with `Sprite:Both Texture2D:Parse`.
- `Texture2D` missing outputs are at least partly real silent no-output conversions. A targeted missing `Font Texture` probe returned 0 and logged `Nothing exported. 1 assets skipped`; a positive-control Texture2D probe using the same filter shape wrote one PNG.
- Existing Texture2D/Sprite accounting overstates clean coverage when multiple map entries predict the same output filename. The wrapper predicts `sanitizedName_p<PathID>.<ext>`, but AnimeStudio export requests are distinct by source file, source offset, type, and PathID. Duplicate predicted paths can overwrite each other on disk while per-entry counting still treats every entry pointing at that path as satisfied.

## Current Evidence From Existing Outputs

StreamingAssets Texture2D status from existing map/output rows:

- matched entries: 126,496
- unique predicted output paths: 126,226
- entries whose predicted path exists: 126,402
- unique existing predicted paths: 126,132
- actual files in `Texture2D/`: 126,132
- missing entries/unique paths: 94
- cross-AB predicted output collision groups: 6
- dirty/uncertain AB source-offset groups from missing outputs or collisions: 341

Representative Texture2D misses include font atlas textures and some terrain/UI/model textures. Persistent Texture2D misses are the six `Font Texture` entries.

Sprite existing output folders were empty in both sources before the wrapper fix. The wrapper-level probe now expands Sprite conversion to:

```text
--types Sprite:Both Texture2D:Parse SpriteAtlas:Parse
```

and produced the sampled `bg_square_fullrect` Sprite PNG.

## Code Changes

- Added wrapper-only convert parse dependencies for Sprite: `Texture2D:Parse` and `SpriteAtlas:Parse`.
- Expanded `--types` centrally in `run_animestudio_stage()` so sharded, normal, and merged calls share the same dependency behavior.
- Added collision-aware asset output status accounting:
  - unique predicted output paths
  - unique existing predicted output paths
  - actual output file count
  - missing unique output count
  - duplicate predicted output path groups
  - cross-AB output collision groups
  - clean/dirty/uncertain source-offset group counts
- Added per-source/type status manifests under:

```text
export_full/recovered/AnimeStudio-cli/<Source>/asset_status/<stage>_<Type>.json
```

Each manifest groups matched conversion map entries by source file plus AB offset, gives a status such as `clean_outputs`, `dirty_missing_output`, or `uncertain_output_collision`, and includes small missing/collision samples. Log export errors remain type-level/unmapped unless AnimeStudio logs gain source/pathID details.

## Verification Commands And Results

```bat
python -m py_compile scripts\export_full_from_game.py
```

Result: passed.

```bat
AnimeStudio.CLI.exe ... --types Texture2D:Both --filter_data texture_missing_filter.json
```

Result: return code 0; logged `Nothing exported. 1 assets skipped` for missing `Font Texture`.

```bat
AnimeStudio.CLI.exe ... --types Texture2D:Both --filter_data texture_existing_filter.json
```

Result: return code 0; logged `Finished exporting 1 assets` and wrote one Texture2D PNG.

```bat
AnimeStudio.CLI.exe ... --types Sprite:Both --filter_data sprite_filter.json
AnimeStudio.CLI.exe ... --types Sprite:Both Texture2D:Parse --filter_data sprite_filter.json
```

Result: both returned 0 with no warnings/errors; plain Sprite wrote no PNG, Sprite plus Texture2D parse wrote one PNG.

```bat
python -c "import export_full_from_game ... run_animestudio_stage(... types=('Sprite:Both',))"
```

Result: wrapper command included `Sprite:Both Texture2D:Parse SpriteAtlas:Parse`, returned 0, and wrote one Sprite PNG under tmp output.

```bat
python -c "import export_full_from_game ... write_animestudio_asset_status_manifest(...)"
```

Result: wrote a tmp Sprite status manifest with `clean_source_group_count=1`, `dirty_source_group_count=0`, `output_entry_count=1`, `missing_output_count=0`.

## Remaining Risks

- No broad Sprite refresh was run; the fix was verified with one targeted Sprite. Atlas-backed Sprites should be better covered by `SpriteAtlas:Parse`, but external atlas/texture dependencies in different bundle offsets may still need dependency-map loading.
- Texture2D silent no-output cases are still treated as unexpected missing outputs except for already allowed Mesh behavior. That is intentional until unsupported Texture2D formats are classified more narrowly.
- Per-AB manifests can map missing outputs and output filename collisions to source ABs, but existing warning/error logs still cannot be mapped exactly to ABs without C# log enrichment that includes source path, offset, PathID, and type.
- Superseded by the follow-up below: `--report-only` previously did not backfill the new manifests because it skipped asset stage finalizers.

## 2026-06-28 Report-Only Status Backfill Follow-Up

Added a wrapper-only report-only status backfill in `scripts/export_full_from_game.py`. In
`--report-only` mode, map-filtered `convert_by_type` plans now load the existing JSON asset map,
apply the same name/container filters, and write per-source/type status manifests without invoking
AnimeStudio conversion. This fills the previous gap where status manifests existed only after a
conversion stage finalizer ran.

Verification commands:

```bat
python -m py_compile scripts\export_full_from_game.py
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-stages convert_by_type --sources Persistent --report-only
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-stages convert_by_type --sources StreamingAssets --report-only
```

Report-only status results from existing maps/outputs:

- `Persistent Texture2D`: matched 5,960, outputs 5,954, missing 6, dirty source groups 89.
- `StreamingAssets Texture2D`: matched 126,496, outputs 126,402, missing 94, dirty source groups 341.
- `Persistent Sprite`: matched 5,603, outputs 0, missing 5,603.
- `StreamingAssets Sprite`: matched 20,917, outputs 0, missing 20,917.

The Sprite report-only totals reproduce the prior 26,520 missing-output count exactly, proving the
current broad export tree is still stale for Sprite; it does not contradict the targeted wrapper
fix. The status manifests are now written under:

```text
export_full/recovered/AnimeStudio-cli/Persistent/asset_status/convert_by_type_Texture2D.json
export_full/recovered/AnimeStudio-cli/Persistent/asset_status/convert_by_type_Sprite.json
export_full/recovered/AnimeStudio-cli/StreamingAssets/asset_status/convert_by_type_Texture2D.json
export_full/recovered/AnimeStudio-cli/StreamingAssets/asset_status/convert_by_type_Sprite.json
```

Concrete targeted probes:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_gap_probe\sprite_plain_20260628_044950" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --filter_data "D:\fluffy-dump\tmp\animestudio_gap_probe\Sprite_bg_square_fullrect_filter.json" --types Sprite:Both
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_gap_probe\sprite_with_deps_20260628_044950" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --filter_data "D:\fluffy-dump\tmp\animestudio_gap_probe\Sprite_bg_square_fullrect_filter.json" --types Sprite:Both Texture2D:Parse SpriteAtlas:Parse
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_gap_probe\texture_font_20260628_044950" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --filter_data "D:\fluffy-dump\tmp\animestudio_gap_probe\Texture2D_Font_Texture_filter.json" --types Texture2D:Both
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_gap_probe\texture_existing_20260628_044950" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --filter_data "D:\fluffy-dump\tmp\animestudio_gap_probe\Texture2D_existing_filter.json" --types Texture2D:Both
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_gap_probe\texture_nonfont_missing_20260628_044950" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --filter_data "D:\fluffy-dump\tmp\animestudio_gap_probe\Texture2D_nonfont_missing_filter.json" --types Texture2D:Both
```

Probe samples and outcomes:

- `Sprite bg_square_fullrect`, pathID `-1508810544388176411`, container
  `assets/beyond/initialassets/prefabs/login/loginrootpanel.prefab`: plain `Sprite:Both` returned 0
  and wrote no file; `Sprite:Both Texture2D:Parse SpriteAtlas:Parse` returned 0 and wrote
  `tmp/animestudio_gap_probe/sprite_with_deps_20260628_044950/Sprite/bg_square_fullrect_pEB0FA0CDCC6105E5.png`.
  Classification: dependency gap, not a Sprite parse failure.
- `Texture2D Font Texture`, pathID `-6603019454663767376`, container
  `assets/beyond/initialassets/ui/fonts/novecentowidebold.otf`: `Texture2D:Both` returned 0 and
  wrote no file. Classification: silent no-output placeholder/unsupported zero-size font texture,
  not a process failure.
- Positive control `Texture2D T_default_mro_MRO`, pathID `-1246962829539794806`, container
  `packages/com.hg.render-pipelines/runtime/renderpipelineresources/material/defaulthgmaterial.mat`:
  same `Texture2D:Both` command shape returned 0 and wrote
  `tmp/animestudio_gap_probe/texture_existing_20260628_044950/Texture2D/T_default_mro_MRO_pEEB1E5E9C92A208A.png`.
- Non-Font missing-status sample `Texture2D 74618664eecd07dc`, pathID `-598241958808313765`, container
  `assets/beyond/dynamicassets/gameplay/ui/sprites/spaceship/spaceshipskillicon/facskill_hub_mine_spd_20.png`:
  same `Texture2D:Both` command shape returned 0 and wrote
  `tmp/animestudio_gap_probe/texture_nonfont_missing_20260628_044950/Texture2D/facskill_hub_mine_spd_20_pF7B29E1BAB7F205B.png`.
  Classification: output identity/name mismatch artifact; the map entry name was the hash-like
  `74618664eecd07dc`, while the exported file used the parsed texture name.

Narrow next command for Sprite broad refresh, if acceptable later:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-stages convert_by_type --sources StreamingAssets Persistent --animestudio-jobs 4 --animestudio-shards 16
```

This will rerun all full-mode conversion types because the current wrapper does not expose a
single-type convert selector. A narrower future wrapper improvement would be a type selector for
`convert_by_type`, but the report-only status backfill is enough to certify that today's 26,520
Sprite misses are stale broad output state plus known parse dependencies.


## 2026-06-28 Texture2D No-Output Diagnostics

Implemented structured AnimeStudio diagnostics for `Texture2D` conversions that return no image:

- `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` logs `[Warning] Texture2D no output ...` when `ConvertToImage(true)` returns null.
- Reasons are narrowly classified as `zero_size_texture`, `empty_image_payload`, or `decode_failed`.
- The warning includes `PathID`, source file/original path, source bundle offset, container, dimensions, texture format, image payload size, stream size/offset, and stream path.
- `scripts/export_full_from_game.py` parses these warnings, including UTF-8 and UTF-16LE logs, and records `texture2d_no_output_count`, `texture2d_no_payload_count`, `texture2d_decode_failed_count`, `classified_no_payload_missing_output_count`, and `suspicious_missing_output_count` in asset status manifests.
- No global `Texture2D` missing-output allow-list was added. A missing Texture2D output is allowed only when a fresh no-payload warning matches the missing record by source leaf, source offset, and PathID. Negative Unity PathIDs are valid and are accepted by the matcher.

Verification commands/results:

```bat
python -m py_compile scripts\export_full_from_game.py
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Both passed; the AnimeStudio build retained only pre-existing project warnings.

Zero-size font probe:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\texture2d_no_output_font_probe_20260628 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --names tmp\animestudio_missing_probe_20260628\texture_missing_names.txt --filter_data tmp\animestudio_missing_probe_20260628\texture_missing_filter.json --types Texture2D:Both
```

Result: exit `0`, no PNG, one structured warning:

```text
reason=zero_size_texture name="Font Texture" PathID=-6603019454663767376 SourceOffset=7661199 Width=0 Height=0 Format=RGBA32 ImageSize=0 StreamSize=0
```

Positive Texture2D probe:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\texture2d_positive_probe_20260628 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --names tmp\animestudio_missing_probe_20260628\texture_existing_names.txt --filter_data tmp\animestudio_missing_probe_20260628\texture_existing_filter.json --types Texture2D:Both
```

Result: exit `0`, wrote `tmp/texture2d_positive_probe_20260628/Texture2D/T_default_mro_MRO_pEEB1E5E9C92A208A.png`, and produced zero Texture2D no-output warnings.

Focused parser/status checks showed:

- The font probe warning parses as `texture2d_no_output_count=1`, `texture2d_no_payload_count=1`, `texture2d_decode_failed_count=0`.
- The matching missing output is classified as `allowed_missing_output`, with `classified_no_payload_missing_output_count=1` and `suspicious_missing_output_count=0`.
- A synthetic `reason=decode_failed` warning remains `dirty_missing_output`, with `texture2d_decode_failed_count=1` and `suspicious_missing_output_count=1`.

Current interpretation: zero-size `Font Texture` rows are understood non-extractable placeholders when confirmed by fresh conversion logs. Report-only manifests from stale outputs still cannot infer this without log evidence, so they should stay suspicious until a real conversion stage emits the structured warning.
