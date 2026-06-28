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
- `--report-only` does not backfill the new manifests because it skips asset stage finalizers; run the relevant convert stage to generate them.
