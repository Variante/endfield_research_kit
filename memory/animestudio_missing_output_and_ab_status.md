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

## 2026-06-28 Focused Sprite Refresh and Name-Mismatch Status

Added a focused wrapper selector:

```bat
python scripts\export_full_from_game.py --animestudio-asset-types Sprite --animestudio-stages convert_by_type --animestudio-scope assets --animestudio-asset-mode full
```

`--animestudio-asset-types` filters the already-defined AnimeStudio asset convert/json type sets after scope/mode expansion. This allows one type, such as `Sprite`, to be refreshed without rerunning `Texture2D`, `Mesh`, and `Animator`.

Status accounting also now resolves valid outputs written under the parsed Unity object name when the asset-map display name differs. If the predicted output path is absent but exactly one output file with the same `_p<PathID>` suffix exists in the type output directory, the status manifest treats the row as exported and records it as `name_mismatch_output_count` instead of `missing_output_count`.

Verification:

```bat
python -m py_compile scripts\export_full_from_game.py
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Sprite --animestudio-stages convert_by_type --sources StreamingAssets --report-only
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Sprite --animestudio-stages convert_by_type --sources StreamingAssets --animestudio-jobs 4 --animestudio-shards 16
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Sprite Texture2D --animestudio-stages convert_by_type --sources StreamingAssets --report-only
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Sprite --animestudio-stages convert_by_type --sources Persistent --animestudio-jobs 4 --animestudio-shards 8
```

Results after the focused Sprite conversion with `Texture2D:Parse` and `SpriteAtlas:Parse` dependencies:

- `StreamingAssets Sprite`: matched `20,917`, output entries `20,917`, actual output files `20,648`, name-mismatch outputs `9`, missing outputs `0`, export errors `0`. Status counts: `9,499` clean groups and `245` output-collision groups.
- `Persistent Sprite`: matched `5,603`, output entries `5,603`, actual output files `5,520`, name-mismatch outputs `0`, missing outputs `0`, export errors `0`. Status counts: `864` clean groups and `83` output-collision groups.

The previous 26,520 Sprite missing-output report was stale output state from the old no-dependency Sprite run, not a Sprite decoder failure. The current verified remaining Sprite caveat is only output collision/name accounting, not missing image export.

Representative StreamingAssets name-mismatch rows now accounted as exported:

- map name `74618664eecd07dc`, PathID `-6901809565594673061`, expected hash-like filename, actual output `facskill_hub_mine_spd_20_pA037D8C47756205B.png`.
- map name `104b9b795a3b894e`, PathID `4024518188806317189`, actual output `bg_sign_char_yvonne_tc_01_p37D9F5F84BE62485.png`.
- map name `5be9c7874cba72f7`, PathID `-5792198476739221886`, actual output `icon_skill_deepfin_01_line_pAF9DFA2C7D666682.png`.

## 2026-06-28 Mesh Allowance Audit

A read-only subagent audit found the current global Mesh no-output allowance is too coarse. It is probably justified for many collision/proxy meshes, but the status data does not prove the missing rows are zero-vertex or missing-vertex-buffer meshes.

Sampled classification from current manifests:

- Total missing Mesh rows across current manifests: `6,152`.
- Sampled missing rows present in manifests: `6,097`.
- Collision/proxy by name/container: `6,062`, e.g. `_COL1_UM01`, `_UCX`, `_col1_...fbx`.
- LOD/proxy/baked/HLOD but not explicitly collision-named: `26`.
- Not clearly advertised as collision/proxy: `9`, including `T_npc_gentleman_backpack_common_c_01_E/D` rows.

Exporter behavior check: `ExportMesh()` silently returns `false` for `m_VertexCount <= 0`, missing/empty `m_Vertices`, or output path setup failure. It does not currently log vertex counts or reason details.

Next concrete improvement: mirror the Texture2D diagnostics for Mesh. Add structured `[Warning] Mesh no output ...` logs with reason, source identity, vertex count, vertex buffer length, submesh/index counts where available; then allow only fresh matched `zero_vertex_count`/`missing_vertex_buffer` rows and leave unmatched Mesh misses suspicious.

## 2026-06-28 Structured Mesh No-Output Diagnostics

Implemented structured Mesh no-output logging in AnimeStudio.CLI for direct OBJ conversion. `ExportMesh()` now emits `[Warning] Mesh no output ...` before returning `false` for:

- `zero_vertex_count` when `m_VertexCount <= 0`.
- `missing_vertex_buffer` when `m_VertexCount > 0` but `m_Vertices == null`.
- `empty_vertex_buffer` when `m_VertexCount > 0` but `m_Vertices.Length == 0`.
- `output_path_unavailable` if output path reservation fails.

The warning includes `PathID`, `SourceFile`, `SourceOriginalPath`, `SourceOffset`, `Container`, `VertexCount`, `VerticesLength`, `SubMeshCount`, `IndexCount`, and object byte size.

Wrapper status handling changed from a global Mesh allow-list to log-backed classification. Missing Mesh OBJ outputs are accepted only when every missing output matches a fresh structured warning with `reason=zero_vertex_count`. Suspicious Mesh reasons such as missing/empty vertex buffers, export errors, or unmatched missing outputs remain dirty. The wrapper also keeps full no-output warning records for matching; samples remain capped for report readability.

Verification commands:

```bat
python -m py_compile scripts\export_full_from_game.py
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Mesh --animestudio-stages convert_by_type --sources Persistent --animestudio-jobs 4 --animestudio-shards 8
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Mesh --animestudio-stages convert_by_type --sources StreamingAssets --animestudio-jobs 4 --animestudio-shards 16
```

Results:

- `Persistent Mesh`: matched `491`, output entries `483`, missing outputs `8`, allowed zero-vertex no-output `8`, suspicious missing outputs `0`, Mesh suspicious warnings `0`, name-mismatch outputs `0`.
- `StreamingAssets Mesh`: matched `59,287`, output entries `53,173`, missing outputs `6,114`, allowed zero-vertex no-output `6,114`, suspicious missing outputs `0`, Mesh suspicious warnings `0`, name-mismatch outputs `30`.

Important intermediate finding: the first StreamingAssets rerun emitted all `6,114` Mesh no-output warnings, but the wrapper initially matched only `20` because matching used capped report samples. Keeping full warning records fixed classification without suppressing anything.

Current interpretation: direct Mesh OBJ missing outputs are now understood for the current export set. They are zero-vertex collision/proxy meshes, not parser failures. The previous global Mesh allowance has been removed; future Mesh missing outputs must be proven by fresh structured logs.

## 2026-06-28 Focused Texture2D Refresh

Reran focused Texture2D conversion after the structured Texture2D no-output diagnostics were in place. The previous `StreamingAssets Texture2D` status with `94` suspicious missing outputs and the old `Persistent Texture2D` status with missing newer summary fields were stale/report-only state, not current decoder evidence.

Verification commands:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Texture2D --animestudio-stages convert_by_type --sources Persistent --animestudio-jobs 4 --animestudio-shards 8
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Texture2D --animestudio-stages convert_by_type --sources StreamingAssets --animestudio-jobs 4 --animestudio-shards 16
```

Fresh report runs:

- `reports/20260628_142702/` for `Persistent` Texture2D.
- `reports/20260628_143746/` for `StreamingAssets` Texture2D.

Results:

- `Persistent Texture2D`: matched `5,960`, output entries `5,954`, actual output files `5,871`, missing outputs `6`, allowed no-payload missing outputs `6`, suspicious missing outputs `0`, decode-failed warnings `0`. Status counts: `1,083` clean groups, `6` allowed-missing groups, `83` collision groups.
- `StreamingAssets Texture2D`: matched `126,496`, output entries `126,490`, actual output files `126,220`, missing outputs `6`, allowed no-payload missing outputs `6`, suspicious missing outputs `0`, decode-failed warnings `0`, name-mismatch outputs `88`. Status counts: `103,969` clean groups, `6` allowed-missing groups, `247` collision groups.

The remaining missing Texture2D outputs are understood: all are `Font Texture` placeholders with `reason=zero_size_texture`, `Width=0`, `Height=0`, `ImageSize=0`, and `StreamSize=0`. There are no fresh Texture2D `decode_failed` warnings and no Texture2D export errors.

Current interpretation: direct Texture2D PNG missing outputs are now understood for the current export set. The remaining non-clean Texture2D groups are output collisions/name accounting, not missing image decode. Future Texture2D missing outputs should continue to require fresh structured no-output warnings.

## 2026-06-28 Residual Asset Target Scan

After the Sprite, Mesh, and Texture2D focused refreshes, current `asset_status` manifests exist for `Texture2D`, `Sprite`, and `Mesh` only. None of those current manifests has suspicious missing output.

A read-only residual scan found:

- `Material` JSON is effectively healthy. The map/output count gap is duplicate PathID/name collapse around `Sprites-Default`, not missing JSON decode: `StreamingAssets Material` has `48,497` map entries and `48,490` JSON files; `Persistent Material` has `1,550` map entries and `1,548` JSON files.
- `Shader` and `AnimationClip` still have old debug-mode export errors (`ShaderConverter` huge aligned-string reads; `AnimationClip` unknown light attributes), but these are lower-priority debug-mode converter paths.
- `Animator` is the next high-value target. It has no asset-status manifest, no current output-quality accounting, and a large map/output gap: `StreamingAssets Animator` has about `57,025` map entries vs `11,526` FBX files, and `Persistent Animator` has about `5,423` map entries vs `1,594` FBX files. Logs from the last full debug run showed no Animator export errors, so the gap likely comes from name/group collapse, GameObject/dependency export behavior, or shallow/empty FBX output rather than ordinary per-asset export exceptions.

Next concrete improvement: add or prototype Animator status accounting that can explain whether each Animator map entry resolves to a meaningful FBX, a duplicate/name-collapsed FBX, or an unsupported/no-mesh FBX export path.

## 2026-06-28 Animator FBX No-Mesh Diagnostics

Animator was the next large apparent gap after Texture2D, Sprite, Mesh, and Material accounting. Before instrumentation, the existing broad debug export looked superficially successful but suspicious:

- `StreamingAssets`: 57,025 Animator map entries, 11,738 unique sanitized Animator/GameObject names, and 11,526 `.fbx` files.
- `Persistent`: 5,423 Animator map entries, 1,606 unique sanitized names, and 1,594 `.fbx` files.
- All existing Animator `.fbx` files were tiny binary FBX containers: `StreamingAssets` ranged from 10,416 to 10,624 bytes, and `Persistent` ranged from 10,416 to 10,576 bytes.
- Probes of representative files found normal `Kaydara FBX Binary` headers but no `Geometry`, `Vertices`, `PolygonVertexIndex`, `Deformer`, or `Animation` markers.

Root cause found in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `TryExportFile()` names normal single-file exports as `<name>_p<PathID>.<ext>`.
- `ExportAnimator()` used `TryExportFolder()`, which names only by `Animator.Name`/linked `GameObject.Name` and loses the per-asset PathID in the final FBX identity.
- `ExportAnimator()` did not check `ModelConverter.MeshList.Count`, so no-mesh Animator conversions produced boilerplate FBX files and returned success.
- `Studio.ExportAssets()` logs hard `Export ... error` entries only for exceptions; converters returning `false` are counted as skipped assets.

Implemented diagnostics:

- `ExportAnimator()` now deletes any stale target `.fbx`, logs `[Warning] Animator no output ...` when `ModelConverter.MeshList.Count == 0`, deletes the empty export folder, and returns `false` instead of emitting a boilerplate FBX.
- The structured warning includes reason, Animator name/PathID, source file/original path, source bundle offset, container, linked GameObject name/PathID, GameObject pointer PathID, Avatar/Controller PathIDs, transform hierarchy flag, mesh/material/texture/animation counts, and intended FBX path.
- `scripts/export_full_from_game.py` parses these warnings, merges them across AnimeStudio runs, writes `animator_no_output_count`, `animator_no_mesh_count`, and `animator_suspicious_no_output_count` into JSON summaries, and surfaces the counts/samples in markdown summaries.

Verification:

```bat
python -m py_compile scripts\export_full_from_game.py
dotnet build tools\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release
```

Both passed. The AnimeStudio build retained only pre-existing warnings.

Focused Animator reruns:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Animator --animestudio-stages convert_by_type --sources Persistent --animestudio-jobs 4 --animestudio-shards 8
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode full --animestudio-asset-types Animator --animestudio-stages convert_by_type --sources StreamingAssets --animestudio-jobs 4 --animestudio-shards 16
```

Results:

| Source | Report run | Return code | Animator warnings | `animator_no_output` | `animator_no_mesh` | Suspicious Animator no-output | Export errors | Remaining Animator `.fbx` files |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Persistent | `reports/20260628_194518` | 0 | 5,423 | 5,423 | 5,423 | 0 | 0 | 0 |
| StreamingAssets | `reports/20260628_194720` | 0 | 57,025 | 57,025 | 57,025 | 0 | 0 | 0 |

Current classification: the old Animator FBX outputs were valid FBX containers but not useful model/animation recovery. Under the current `Animator:Both` export surface, all Animator map rows are now explicitly understood as `no_mesh` no-output conversions, not silent successful model exports.

Remaining technical question: this does not yet prove that every original Animator-linked GameObject truly lacks mesh data. The current explicit Animator type slice may still under-parse some renderer, mesh, transform, controller, or clip dependencies. The next useful experiment is a narrow Animator dependency probe that adds parse-only `Transform`, `MeshRenderer`, `SkinnedMeshRenderer`, `MeshFilter`, `Mesh`, `Avatar`, `AnimatorController`, and `AnimationClip` where supported, then compares `MeshCount` and `AnimationCount` against the fresh no-mesh baseline.
## 2026-06-28 AnimationClip Light Attribute Recovery

The last broad debug report, `reports/20260627_215637`, showed AnimationClip converter failures:

- `StreamingAssets`: matched `117,849`, missing `67`, export errors `42`.
- `Persistent`: matched `7,984`, missing `8`, export errors `8`.
- Error signatures were mostly `Unknown attribute 44543834 for Light` (`46` cases) and `Unknown attribute 1127824095 for Light` (`3` cases), plus one unknown custom type `39` case.

Current source already contained the earlier generic fallback from `fbbe855 Recover shader and animation export fallbacks`, so a fresh focused rerun was needed before changing parser behavior.

Focused verification command:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode debug --animestudio-asset-types AnimationClip --animestudio-stages convert_by_type --sources Persistent StreamingAssets --animestudio-jobs 4 --animestudio-shards 16
```

Fresh report run: `reports/20260628_200522`.

Results:

| Source | Matched AnimationClip entries | Output entries | Missing outputs | Export errors | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: |
| Persistent | 7,984 | 7,984 | 0 | 0 | 0 |
| StreamingAssets | 117,849 | 117,849 | 0 | 0 | 0 |

Interpretation: current AnimationClip conversion no longer has hard export errors for the Light/custom-type cases. However, the fresh `.anim` outputs still used generic fallback property names:

- `unknown_Light_44543834`
- `unknown_Light_1127824095`
- `unknown_CustomType39_*`

Implemented semantic recovery in `tools/AnimeStudio/AnimeStudio.Utility/YAML/CustomCurveResolver.cs`:

- `44543834` now resolves through `CRC.CalculateDigestAscii("m_InnerSpotAngle")` to `m_InnerSpotAngle`.
- `1127824095` now resolves through `CRC.CalculateDigestAscii("m_BounceIntensity")` to `m_BounceIntensity`.
- Generic fallback remains for truly unknown attributes/custom types.

Verification:

```bat
dotnet build tools\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_animationclip_light_probe\output" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --names "D:\fluffy-dump\tmp\animestudio_animationclip_light_probe\names.txt" --filter_data "D:\fluffy-dump\tmp\animestudio_animationclip_light_probe\filter_data.json" --types AnimationClip:Both
```

The two-row probe wrote:

- `LightingDeco_dung01_rdg003_01_openidle_p893EF00E0114EDF4.anim` with `attribute: m_InnerSpotAngle`.
- `P_wolfgd_ultskill_start_light_p3DEF450124FD0D8A.anim` with `attribute: m_BounceIntensity`.

Then the main export tree was refreshed in-place for all affected Light clips using exact temporary filter data:

- `StreamingAssets`: `41` affected AnimationClip entries.
- `Persistent`: `8` affected AnimationClip entries.

Post-refresh checks:

```bat
rg -n "unknown_Light_44543834|unknown_Light_1127824095" export_full\recovered\AnimeStudio-cli\StreamingAssets\convert_by_type\AnimationClip export_full\recovered\AnimeStudio-cli\Persistent\convert_by_type\AnimationClip -g "*.anim"
rg -n "m_InnerSpotAngle|m_BounceIntensity" export_full\recovered\AnimeStudio-cli\StreamingAssets\convert_by_type\AnimationClip export_full\recovered\AnimeStudio-cli\Persistent\convert_by_type\AnimationClip -g "*.anim"
```

Result: no old `unknown_Light_*` names remain; all known Light property hashes now appear as `m_InnerSpotAngle` or `m_BounceIntensity` in the refreshed export tree.

Remaining AnimationClip unknown:

```text
export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip/P_agtrinit_skill232_summon_02_ready_p7C8609B936A31E0C.anim
```

This file still has three `unknown_CustomType39_*` attributes. That is no longer an export failure, but it is still a semantic gap and should be investigated separately instead of silently suppressing it.

## 2026-06-28 AnimationClip ParticleSystemForceField Recovery

Follow-up on the remaining `unknown_CustomType39_*` attributes from `P_agtrinit_skill232_summon_02_ready_p7C8609B936A31E0C.anim`.

Evidence:

- The three unknown curves had `classID: 330`, `customType: 39`, and attributes `1865675821`, `2217896801`, and `1185939899`.
- `tools/AnimeStudio/AnimeStudio/ClassIDType.cs` maps class ID `330` to `ParticleSystemForceField`.
- Local TypeTree evidence in `tools/TypeTree/Common/6000.1.0f1.json` and `tools/TypeTree/2/3.0.0/info.json` shows `ParticleSystemForceFieldParameters` fields under `m_Parameters`, including `m_StartRange`, `m_EndRange`, and `m_GravityFocus`.
- The same CRC path used by `CustomCurveResolver` matches:
  - `m_Parameters.m_EndRange` -> `1865675821` / `0x6F33F42D`
  - `m_Parameters.m_GravityFocus` -> `2217896801` / `0x84326B61`
  - `m_Parameters.m_StartRange` -> `1185939899` / `0x46B001BB`

Implemented semantic recovery in AnimeStudio:

- Added `ParticleSystemForceField = 39` to `BindingCustomType`.
- Added a `CustomCurveResolver` case that maps only the three evidence-backed `ParticleSystemForceField` parameter fields above.
- Generic fallback remains for any other unknown `ParticleSystemForceField` attribute.

Focused verification command:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_animationclip_forcefield_probe\output" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --names "D:\fluffy-dump\tmp\animestudio_animationclip_forcefield_probe\names.txt" --filter_data "D:\fluffy-dump\tmp\animestudio_animationclip_forcefield_probe\filter_data.json" --types AnimationClip:Both
```

Probe result:

- `attribute: m_Parameters.m_EndRange` at line `629`.
- `attribute: m_Parameters.m_GravityFocus` at line `656`.
- `attribute: m_Parameters.m_StartRange` at line `2223`.
- No `unknown_CustomType39_*` remained in the focused output.

Then the main export tree was refreshed in-place for that exact AnimationClip row:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\StreamingAssets\convert_by_type" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --names "D:\fluffy-dump\tmp\animestudio_animationclip_forcefield_probe\names.txt" --filter_data "D:\fluffy-dump\tmp\animestudio_animationclip_forcefield_probe\filter_data.json" --types AnimationClip:Both
```

Current classification: the former `CustomType39` AnimationClip gap is a `ParticleSystemForceField` binding, not encryption and not malformed AnimationClip data. The remaining unresolved part in this specific clip is path recovery (`path_1620762661` still has no resolved GameObject path), but the animated field names are now understood.

## 2026-06-28 Current Shader Refresh Status

A full focused Shader refresh with the current AnimeStudio binary replaced the stale `reports/20260627_215637` Shader failure picture:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode debug --animestudio-asset-types Shader --animestudio-stages convert_by_type --sources Persistent StreamingAssets --animestudio-jobs 4 --animestudio-shards 16
```

Fresh report run: `reports/20260628_204551`.

Results:

| Source | Matched Shader entries | Missing outputs | Export errors | Current blocker |
| --- | ---: | ---: | ---: | --- |
| Persistent | 222 | 1 | 1 | `Shader:HGRP/CharacterNPR` |
| StreamingAssets | 271 | 1 | 1 | `Shader:HGRP/CharacterNPR` |

Interpretation:

- The old broad class of `ReadAlignedString requests ...` Shader failures is no longer the current blocker.
- Focused probes for `Mobile/Particles/Additive` and `HGRP/WaterForwardRendering` both wrote `.shader` files with parsed Endfield DXBC/SMOL-V snippets and no `AnimeStudio shader bytecode unavailable` fallback marker.
- The distinct old `HGRP/WaterForwardRendering` negative `ReadBytes` case is now parsed/exported as real snippet output.
- The only current Shader export failure is `HGRP/CharacterNPR`, mirrored in both roots with the same PathID `-7822190029627442914`.

Current `HGRP/CharacterNPR` evidence:

- `Persistent`: source `D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\0CE8FA57\FCF21734CEDE10386D06530C787F510D.chk`, expected output `HGRP_CharacterNPR_p9371FF9C9E74391E.shader`.
- `StreamingAssets`: source `D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk`, expected output `HGRP_CharacterNPR_p9371FF9C9E74391E.shader`.
- Both logs throw `System.OutOfMemoryException` at `StringBuilder.ToString()` inside `ShaderConverter.ConvertSerializedSubShader`.

Current classification: the remaining Shader blocker is not VFS decode, bundle encryption, or the old Endfield shader subprogram schema gap. It is an exporter scalability/output construction problem for one very large shader. The next useful patch should preserve parsed subprogram metadata and bytecode hashes without constructing an unbounded single decompiled text string.

## 2026-06-28 CharacterNPR Shader Export Recovery

Follow-up on the `HGRP/CharacterNPR` Shader OOM from `reports/20260628_204551`.

Implemented a bounded shader body writer in `tools/AnimeStudio/AnimeStudio.Utility/ShaderConverter.cs`:

- Per-shader generated program text is capped at `32 MiB`.
- Parsed bytecode identity comments, offsets, sizes, hashes, keywords, and pass/subprogram structure are still emitted.
- Once the cap is reached, later large decompiled/source bodies are replaced with an explicit `AnimeStudio: omitted ... shader program text budget` comment instead of forcing one unbounded `StringBuilder`/decompiler output path.
- SPIR-V and Endfield DXBC HLSL decompilation are skipped once the cap is exhausted, so the exporter avoids spending time and memory on text that cannot be appended.

Focused verification:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_shader_characternpr_probe\output" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --names "D:\fluffy-dump\tmp\animestudio_shader_characternpr_probe\names.txt" --filter_data "D:\fluffy-dump\tmp\animestudio_shader_characternpr_probe\filter_data.json" --types Shader:Both
```

Probe result:

- Exit code `0`.
- Wrote `HGRP_CharacterNPR_p9371FF9C9E74391E.shader`.
- Output size: `36,356,198` bytes.
- The output includes parsed Endfield DXBC and SMOL-V snippet metadata plus budget comments for omitted decompiled bodies after the cap is reached.

Full focused Shader refresh:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode debug --animestudio-asset-types Shader --animestudio-stages convert_by_type --sources Persistent StreamingAssets --animestudio-jobs 4 --animestudio-shards 16
```

Fresh report run: `reports/20260628_212932`.

Results:

| Source | Matched Shader entries | Missing outputs | Export errors |
| --- | ---: | ---: | ---: |
| Persistent | 222 | 0 | 0 |
| StreamingAssets | 271 | 0 | 0 |

Current classification: `HGRP/CharacterNPR` is understood enough to export reliably. The prior failure was not encryption, VFS decode, or shader bytecode schema loss; it was unbounded text generation for one exceptionally large shader. Remaining semantic limitation: after the 32 MiB cap, some decompiled/source bodies are intentionally omitted, but their parsed bytecode metadata and hashes remain in the `.shader` output for identity and follow-up analysis.

## 2026-06-28 Empty Mesh and Font Texture Marker Recovery

Follow-up on the remaining classified missing outputs in the current asset-status manifests after Shader and AnimationClip recovery.

### Zero-Vertex Mesh

Before this change, Mesh conversion had no hard export errors, but the wrapper still reported classified missing outputs because AnimeStudio parsed zero-vertex Unity Mesh objects and returned `false` before writing `.obj` files:

- `Persistent`: `491` matched Mesh entries, `8` allowed missing outputs.
- `StreamingAssets`: `59,287` matched Mesh entries, `6,114` allowed missing outputs.

The sampled objects are parsed Unity Mesh records with `VertexCount=0`, `VerticesLength=0`, and `IndexCount=0`, often collision/import placeholder names such as `_COL1_UM01`, `_UBX`, `_UCX`, or `Collider`. These are not VFS decode failures, not encryption, and not malformed Mesh payloads.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `ExportMesh` now writes a comment-only `.obj` marker for `m_VertexCount <= 0` instead of logging `Mesh no output` and returning `false`.
- The marker preserves reason, name, PathID, source file, source offset, vertex/submesh/index counts, and byte size.
- Nonzero-vertex Mesh failures such as missing/empty vertex buffers still log as warnings and fail normally.

Focused probe:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_mesh_empty_probe" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --names "D:\fluffy-dump\tmp\animestudio_mesh_empty_probe\names.txt" --filter_data "D:\fluffy-dump\tmp\animestudio_mesh_empty_probe\filter_data.json" --types Mesh:Both
```

Probe result: `S_waterquad_Collider_pA66CEA02CDDFF64B.obj` was written with `# AnimeStudio empty Mesh` metadata and no warning output.

Full focused Mesh refresh: `reports/20260628_214905`.

| Source | Matched Mesh entries | Output entries | Missing outputs | Export errors |
| --- | ---: | ---: | ---: | ---: |
| Persistent | 491 | 491 | 0 | 0 |
| StreamingAssets | 59,287 | 59,287 | 0 | 0 |

### Font Texture Placeholders

Before this change, each root had six classified Texture2D missing outputs. All six are `Font Texture` subobjects for font assets (`.ttf`/`.otf`) with `Width=0`, `Height=0`, `ImageSize=0`, `StreamSize=0`, and empty `StreamPath`. They are true empty Unity font-placeholder textures, not missing external texture streams and not decode failures.

Implemented in AnimeStudio and the wrapper:

- AnimeStudio now recognizes the exact zero-size `Font Texture` placeholder shape and writes `<name>_p<PathID>.png.empty.json` instead of logging a warning or synthesizing fake pixels.
- The marker records reason `font_placeholder_zero_size_texture`, source identity, dimensions, format, image/stream sizes, and byte size.
- `scripts/export_full_from_game.py` now treats Texture2D marker suffixes as valid output candidates by PathID, while generic `zero_size_texture` and `empty_image_payload` warnings are no longer blanket-allowed.

Focused probe:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_texture_font_placeholder_probe" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --names "D:\fluffy-dump\tmp\animestudio_texture_font_placeholder_probe\names.txt" --filter_data "D:\fluffy-dump\tmp\animestudio_texture_font_placeholder_probe\filter_data.json" --types Texture2D:Both
```

Probe result: `Font Texture_pA45D5CCA4FC5CAB0.png.empty.json` was written with `font_placeholder_zero_size_texture` metadata and no warning output.

Texture2D verification:

- The full wrapper run `reports/20260628_221139` timed out before queueing shards 15 and 16, but all launched shard processes finished cleanly and logs contained no `Texture2D no output`, `Export Texture2D`, `[Error]`, `[Warning]`, or exception lines.
- Shards 15 and 16 were then run directly with the existing generated filter files.
- Report-only status was regenerated in `reports/20260628_231334`.

| Source | Matched Texture2D entries | Output entries | Marker outputs | Missing outputs | Export errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| Persistent | 5,960 | 5,960 | 6 | 0 | 0 |
| StreamingAssets | 126,496 | 126,496 | 6 | 0 | 0 |

Current classification: zero-vertex Meshes and zero-size `Font Texture` objects are now preserved as explicit metadata outputs rather than missing files. This improves understanding instead of suppressing warnings: generic malformed Mesh/Texture2D cases still remain visible, while the proven empty placeholder cases now have durable output artifacts.

Remaining non-error report noise after this pass is identity accounting, not decode failure: `name_mismatch_output_count` and `uncertain_output_collision` groups for shared assets and Texture2D raw-hash collisions still need a separate status-model patch.

## 2026-06-28 Output Collision Status Split

Follow-up on the remaining identity-accounting noise after Mesh and Texture2D marker recovery.

Implemented in `scripts/export_full_from_game.py`:

- Output-path reuse is now classified instead of treated as one broad collision bucket.
- Same output path with identical `Type`, `PathID`, `Name`, and map `Hash` across multiple AB groups is reported as `shared_output_reference`.
- Same output path with identical `Type`, `PathID`, and `Name` but differing map `Hash` is reported as `raw_hash_output_collision`.
- Same output path with differing identity fields is reported as `identity_output_collision`.
- Same-output duplicates within one AB group remain `uncertain_duplicate_output_path`.
- `reports/export_full_summary.md` now prints `cross_ab_paths`, `shared_refs`, `raw_hash_collisions`, `identity_collisions`, and `uncertain_collisions` separately.

Verification command:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode debug --animestudio-asset-types Texture2D Sprite Shader AnimationClip Mesh --animestudio-stages convert_by_type --sources Persistent StreamingAssets --report-only
```

Fresh report run: `reports/20260628_232303`.

| Source | Type | Matched entries | Output entries | Missing outputs | Shared refs | Raw-hash collisions | Identity collisions | Dirty groups |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Persistent | AnimationClip | 7,984 | 7,984 | 0 | 0 | 0 | 0 | 0 |
| Persistent | Mesh | 491 | 491 | 0 | 0 | 0 | 0 | 0 |
| Persistent | Shader | 222 | 222 | 0 | 3 | 0 | 0 | 0 |
| Persistent | Sprite | 5,603 | 5,603 | 0 | 3 | 0 | 0 | 0 |
| Persistent | Texture2D | 5,960 | 5,960 | 0 | 0 | 3 | 0 | 83 |
| StreamingAssets | AnimationClip | 117,849 | 117,849 | 0 | 0 | 0 | 0 | 0 |
| StreamingAssets | Mesh | 59,287 | 59,287 | 0 | 0 | 0 | 0 | 0 |
| StreamingAssets | Shader | 271 | 271 | 0 | 3 | 0 | 0 | 0 |
| StreamingAssets | Sprite | 20,917 | 20,917 | 0 | 5 | 0 | 0 | 0 |
| StreamingAssets | Texture2D | 126,496 | 126,496 | 0 | 0 | 6 | 0 | 247 |

Current classification: all five manifest-covered conversion types have complete outputs and zero export errors in the latest report-only manifests. Shader and Sprite output-path reuse is now understood as shared references, not dirty export status. The only remaining dirty status is Texture2D raw-hash-only reuse: identical output name and PathID, but differing map `Hash` across source containers. That is not evidence of missing VFS bytes or failed decryption, but the hash field semantics are not fully understood yet, so it remains visible rather than being downgraded to clean.

## 2026-06-28 Texture2D Raw-Hash Collision Resolution

Follow-up on the Texture2D `raw_hash_output_collision` bucket from `reports/20260628_232303`.

### Hash Semantics

AnimeStudio asset-map `Hash` is not an exported PNG hash and not a compressed/encrypted VFS-byte hash.

Code audit:

- `tools/AnimeStudio/AnimeStudio/AssetsHelper.cs` builds map entries by constructing a base `Object` and assigning `Hash = obj.GetHash()`.
- `tools/AnimeStudio/AnimeStudio/Classes/Object.cs` implements the default `GetHash()` as `XXH64.DigestOf(GetRawData()).ToString("x")`.
- `GetRawData()` reads the Unity serialized-file object byte slice from `byteStart` for `byteSize`.
- For `Texture2D`, externally streamed texture bytes are not included in this default map hash; the raw serialized object records include stream metadata such as path, offset, and size. The image-hash override path exists but is not used by the asset-map builder.

Implication: different map `Hash` values for the same `Type`, `PathID`, and `Name` mean distinct raw serialized object records, not necessarily distinct decoded image payloads. This points to duplicated/equivalent serialized records or container-specific metadata, not to failed decryption or parser loss by itself.

### Data Audit

Generated local reports:

- `reports/texture2d_raw_hash_collision_audit.md`
- `reports/texture2d_raw_hash_collision_audit.json`

Current Texture2D raw-hash output groups:

| Source | Output artifact | Entries | PNG size | PNG SHA-256 prefix |
| --- | --- | ---: | ---: | --- |
| Persistent | `Background_p59E0F9C8D2F90F4C.png` | 77 | 709 B | `5859518c3401ce69` |
| Persistent | `UIMask_p968E5260DA470F4C.png` | 2 | 251 B | `5455f2d48fa4d0a1` |
| Persistent | `UISprite_p39CC623422330F4C.png` | 7 | 761 B | `8c25472076094ec5` |
| StreamingAssets | `Background_p59E0F9C8D2F90F4C.png` | 126 | 709 B | `5859518c3401ce69` |
| StreamingAssets | `InputFieldBackground_pFF9E60FF3ED20F4C.png` | 2 | 813 B | `5c1e83125255a8f9` |
| StreamingAssets | `Knob_pA35E39E3A5CB0F4C.png` | 8 | 1,931 B | `dbbe2200ace011eb` |
| StreamingAssets | `T_wpn_sword_0009_01_D_p666E9D8C5CA0F2E9.png` | 2 | 1,405,471 B | `074e76c38fa6093a` |
| StreamingAssets | `UIMask_p968E5260DA470F4C.png` | 15 | 251 B | `5455f2d48fa4d0a1` |
| StreamingAssets | `UISprite_p39CC623422330F4C.png` | 123 | 761 B | `8c25472076094ec5` |

All rows in these groups match real map entries. For every group, map `Type`, `PathID`, and `Name` are constant; the varying fields are `Hash`, `Container`, `Offset`, and, for StreamingAssets, sometimes `Source`.

### Isolated Decode Verification

Generated local reports:

- `reports/texture2d_raw_hash_collision_isolated_verify.md`
- `reports/texture2d_raw_hash_collision_isolated_verify.json`

Verification method:

1. For each of the 362 raw-hash collision map rows, write a one-entry `filter_data` file with that row's `Source`, `Offset`, `Name`, `PathID`, and `Type`.
2. Run AnimeStudio.CLI with an impossible `--names` regex so normal name matching selects nothing and `filter_data` identity matching selects only the target object.
3. Confirm exactly one target PNG is written.
4. Compare the isolated PNG SHA-256 to the existing shared output artifact SHA-256.

Summary:

| Checked entries | Matched expected PNG SHA-256 | Mismatched or missing | Command failures | Elapsed |
| ---: | ---: | ---: | ---: | ---: |
| 362 | 362 | 0 | 0 | 194.648 s |

Per output group:

| Source | Output | Checked | Matched | Failures | Mismatches |
| --- | --- | ---: | ---: | ---: | ---: |
| Persistent | `Background_p59E0F9C8D2F90F4C.png` | 77 | 77 | 0 | 0 |
| Persistent | `UIMask_p968E5260DA470F4C.png` | 2 | 2 | 0 | 0 |
| Persistent | `UISprite_p39CC623422330F4C.png` | 7 | 7 | 0 | 0 |
| StreamingAssets | `Background_p59E0F9C8D2F90F4C.png` | 126 | 126 | 0 | 0 |
| StreamingAssets | `InputFieldBackground_pFF9E60FF3ED20F4C.png` | 2 | 2 | 0 | 0 |
| StreamingAssets | `Knob_pA35E39E3A5CB0F4C.png` | 8 | 8 | 0 | 0 |
| StreamingAssets | `T_wpn_sword_0009_01_D_p666E9D8C5CA0F2E9.png` | 2 | 2 | 0 | 0 |
| StreamingAssets | `UIMask_p968E5260DA470F4C.png` | 15 | 15 | 0 | 0 |
| StreamingAssets | `UISprite_p39CC623422330F4C.png` | 123 | 123 | 0 | 0 |

Current classification: the Texture2D raw-hash bucket is understood for the current export. It consists of distinct Unity serialized Texture2D records that decode to identical PNG bytes under the same AnimeStudio output filename. It is not missing VFS data, not evidence of double encryption, and not parser loss. The exporter overwrite behavior is harmless for this current dataset because isolated per-row exports produce byte-identical PNGs, but future raw-hash collisions should still remain report-visible until similarly verified.

## 2026-06-28 Alternate Output Name Taxonomy

Follow-up on `name_mismatch_output_count` after all outputs were present.

Affected current status manifests:

| Source | Type | Name mismatches | Marker outputs | Missing/suspicious |
| --- | --- | ---: | ---: | --- |
| StreamingAssets | AnimationClip | 25 | 0 | 0 / 0 |
| StreamingAssets | Mesh | 36 | 0 | 0 / 0 |
| StreamingAssets | Sprite | 9 | 0 | 0 / 0 |
| StreamingAssets | Texture2D | 94 | 6 | 0 / 0 |
| Persistent | Texture2D | 6 | 6 | 0 / 0 |

Classified 170 alternate output-name cases:

| Class | Count | Meaning |
| --- | ---: | --- |
| Marker suffix | 12 | Predicted primary `.png`, actual `.png.empty.json`; all are `Font Texture` empty texture markers. |
| Container leaf / import name | 109 | Map `Name` is a hash, bundle path, or stale alternate name while AnimeStudio writes the container leaf or import asset name. |
| Runtime asset name | 49 | AnimeStudio writes the parsed Unity object/runtime name rather than map `Name` or simple container leaf. |
| Case/normalization subset | 88 | Actual name differs by capitalization/import normalization, such as `terrain_4_0_14_a` to `Terrain_4_0_14_A`. |

Examples:

- Marker suffix: `Font Texture`, container `assets/beyond/initialassets/ui/fonts/novecentowidebold.otf`; predicted `.png`, actual `.png.empty.json`.
- Container leaf: Texture2D map `Name=74618664eecd07dc`, container `.../facskill_hub_mine_spd_20.png`, actual `facskill_hub_mine_spd_20_pF7B29E1BAB7F205B.png`.
- Runtime asset name: Sprite map `Name=9df45a8f9df81019`, container `.../charformationpanel.prefab`, actual `icon_btn_contingency_p6A4D142CF2A6F849.png`.
- Empty map name: Mesh map `Name=""`, container `.../s_fx_ui_skateboard_901.fbx`, actual `Mesh#24234_p0DE76DF9B6DE6B71.obj`.
- AnimationClip runtime name: map `Name=3d86be51a7d2a8b6`, container `.../dlgtl_e6m3_10_sub_1_actor.playable`, actual `Recorded (1428)_pB2B38651C51CA788.anim`.

Current classification: name mismatches are reporting/name-prediction limitations, not missing export data or parser loss. The wrapper resolves them by unique PathID output candidate, and all affected manifests report zero missing outputs, zero suspicious missing outputs, and zero export errors. A future wrapper improvement should rename this bucket to alternate output names and carry fields such as `actual_output_base`, `predicted_output_base`, `name_mismatch_reason`, `resolved_by_path_id`, and `name_source_hint`.

Implemented follow-up in `scripts/export_full_from_game.py`:

- `name_mismatch_output_count` is preserved for compatibility.
- New `alternate_name_output_count`, `alternate_name_reason_counts`, `alternate_name_source_hint_counts`, `alternate_name_case_normalized_count`, and `alternate_name_output_samples` fields are written to asset-status summaries.
- Alternate-name samples now include `actual_output_base`, `predicted_output_base`, `map_name`, `container_leaf_stem`, `name_mismatch_reason`, `name_source_hint`, `case_normalized`, `map_case_normalized`, `container_leaf_case_normalized`, and `resolved_by_path_id`.
- `reports/export_full_summary.md` asset-cache lines now include `alternate_names=...`.

Verification run: `reports/20260628_234435`.

Final alternate-name reason counts:

| Source | Type | Count | Reason counts | Case-normalized subset |
| --- | --- | ---: | --- | ---: |
| Persistent | Texture2D | 6 | `marker_suffix=6` | 0 |
| StreamingAssets | AnimationClip | 25 | `container_leaf=7`, `runtime_asset_name=18` | 3 |
| StreamingAssets | Mesh | 36 | `container_leaf=15`, `empty_map_name=1`, `runtime_asset_name=20` | 15 |
| StreamingAssets | Sprite | 9 | `container_leaf=8`, `runtime_asset_name=1` | 0 |
| StreamingAssets | Texture2D | 94 | `container_leaf=79`, `marker_suffix=6`, `runtime_asset_name=9` | 70 |

Current classification after implementation: alternate names are now a first-class report bucket rather than an unexplained warning-like counter. They remain visible, but no longer imply missing export data.

## 2026-06-29 Animator No-Mesh Marker Recovery

Follow-up on the remaining `Animator` convert gap. Prior logs showed parsed `Animator` objects returning no FBX with `reason=no_mesh`; this was not a VFS/decryption failure, but a Unity object whose resolved hierarchy contains no Mesh objects, so no geometry can be emitted.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `ExportAnimator` now writes `<name>_p<PathID>.fbx.empty.json` for `no_mesh` Animator objects instead of logging `Animator no output` and returning `false`.
- The marker preserves source file/original path, source offset, PathID, container, GameObject name and pointer PathID, Avatar/Controller PathIDs, transform hierarchy flag, mesh/material/texture/animation counts, and byte size.
- Non-marker output-path failures still log `Animator no output` and fail normally.

Implemented in `scripts/export_full_from_game.py`:

- Animator convert outputs are now tracked as `.fbx` with marker suffix `.fbx.empty.json`.
- Report-only asset status generation no longer skips map-filter-unsafe types. This does not change actual Animator export behavior; Animator still runs on the broad dependency-loading path, but status manifests can now be generated from the asset map plus existing outputs.

Focused probe:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_animator_empty_probe\out" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --filter_data "D:\fluffy-dump\tmp\animestudio_animator_empty_probe\filter.json" --names "D:\fluffy-dump\tmp\animestudio_animator_empty_probe\names.txt" --types Animator:Both
```

Probe result: exit `0`, no warnings/errors, wrote `Animator/lattice_p0000000000000028.fbx.empty.json` with `reason=no_mesh`, `pathId=40`, `sourceOffset=8945913`, `gameObjectName=lattice`, and all mesh/material/texture/animation counts equal to `0`.

Full focused Animator refresh:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode debug --animestudio-stages convert_by_type --animestudio-asset-types Animator --sources StreamingAssets Persistent --animestudio-jobs 2
python scripts\export_full_from_game.py --report-only --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode debug --animestudio-stages convert_by_type --animestudio-asset-types Animator --sources StreamingAssets Persistent --animestudio-jobs 2
```

Fresh runs:

- Export run: `reports/20260629_010651`, both AnimeStudio commands returned `0`.
- Report-only status run: `reports/20260629_011358`.

| Source | Matched Animator entries | Output entries | Marker outputs | Missing outputs | Export errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| StreamingAssets | 57,025 | 57,025 | 57,025 | 0 | 0 |
| Persistent | 5,423 | 5,423 | 5,423 | 0 | 0 |

The focused run logs contain no `[Warning]`, `[Error]`, `Exception`, `Animator no output`, or `Export ... error` matches. Current classification: Endfield Animator assets in the current dataset are understood as no-mesh Animator records, and are now preserved as explicit metadata markers rather than missing FBX files or suppressed warnings.

## 2026-06-29 Marker vs Alternate-Name Report Split

Follow-up on the combined six-type report after Animator marker recovery.

The first combined status pass with Animator included showed `name_mismatch_output_count` and `alternate_name_output_count` both increasing by every marker file because marker suffixes intentionally differ from the primary output suffix (`.png` -> `.png.empty.json`, `.fbx` -> `.fbx.empty.json`). This was technically visible but misleading: marker outputs are already first-class evidence through `marker_output_count` and should not imply a Unity-name prediction ambiguity.

Implemented in `scripts/export_full_from_game.py`:

- `marker_output_count` remains unchanged and now has `marker_output_samples`.
- `name_mismatch_output_count` remains compatibility-compatible and still includes marker suffix differences.
- `alternate_name_output_count`, reason counts, source-hint counts, case-normalized counts, and alternate-name samples now exclude marker outputs and represent only non-marker alternate filenames.

Verification:

```bat
python -m py_compile scripts\export_full_from_game.py
python scripts\export_full_from_game.py --report-only --skip-structured --skip-vfs-index --animestudio-scope assets --animestudio-asset-mode debug --animestudio-stages convert_by_type --animestudio-asset-types Texture2D Sprite Shader AnimationClip Mesh Animator --sources Persistent StreamingAssets --animestudio-jobs 2
```

Fresh report run: `reports/20260629_012423`.

Key results:

| Source | Type | Markers | Name mismatches | Alternate names |
| --- | --- | ---: | ---: | ---: |
| Persistent | Texture2D | 6 | 6 | 0 |
| Persistent | Animator | 5,423 | 5,423 | 0 |
| StreamingAssets | Texture2D | 6 | 94 | 88 |
| StreamingAssets | Animator | 57,025 | 57,025 | 0 |

Current classification: marker outputs remain visible, but marker suffixes are no longer mixed into the alternate-output-name taxonomy. The actual non-marker alternate-name cases remain Texture2D/Sprite/Mesh/AnimationClip import/runtime-name differences, not missing export data.

## 2026-06-29 ManagedReference Slash-Class Recovery

Follow-up on current `MonoBehaviour` JSON warnings after the June 29 Animator/report fixes. A fresh focused story JSON refresh was started with:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index --animestudio-scope story --animestudio-stages json_by_type --sources StreamingAssets Persistent --animestudio-jobs 2
```

The run timed out after 30 minutes while still in `StreamingAssets`, so `reports/export_full_summary.*` was not updated. The partial log under `reports/20260629_015041/StreamingAssets/StreamingAssets_animestudio_json_by_type.stdout.log` is still useful current evidence: it contained 221 `Partially decoded MonoBehaviour ... references:ManagedReferencesRegistry` warnings and no `Export ... error` lines.

Representative warning objects:

| Name | PathID | Source offset | Registry count | Recovery blocker |
| --- | ---: | ---: | ---: | --- |
| `BB_npc_coilbst_base` | `-9211232085422307876` | `222272963` | 5 | class names like `NPCCoilbstEscapeBehavior/NPCCoilbstEscapeBehaviorData` |
| `BB_eny_0107_wgshoal2_hdg20` | `2513012069621001524` | `817626320` | 2 | class names like `EnemyBattleGraph/EnemyBattleGraphData` |
| `WeaponWallDisplayConfig` | `-9197814539915967567` | `67312943` | 5 | class names like `WeaponWallDisplayConfig/WeaponDisplayConfig` |

Raw sidecar probes showed valid `ManagedReferencesRegistry` bytes at the stopped offsets. The parser failure was `LooksLikeManagedReferenceClassName`, which rejected `/` even though Unity serializes these nested managed-reference class names as `Outer/Inner`. The namespace and assembly strings remained normal runtime values such as `Beyond.Gameplay.AI` and `Gameplay.Beyond`.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `LooksLikeManagedReferenceClassName` now accepts `/` inside class names.
- Namespace and assembly validation remains unchanged.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Build result: success, `0 Warning(s)`, `0 Error(s)`.

Three-object raw repro after the fix wrote top-level `references` for all three samples, with `managedReferencesRegistryRecovered=true`, zero log warning/error lines, and heuristic `RefIds` entries preserving type, offset, length, string hints, and RID links where available.

A broader targeted repro used the 221 warning PathIDs from `reports/20260629_015041` and the asset map to build `tmp/monobehaviour_warning_221_after_slash/filter.json`, then exported only those source offsets. Result:

| Metric | Count |
| --- | ---: |
| Warning PathIDs covered by filter | 221 / 221 |
| Exported JSONs from selected source offsets | 15,014 |
| CLI warning/error lines | 0 |
| JSONs with `partialTypeTreeDecode` / `partialTypeTreeError` | 0 |
| `managedReferencesRegistryRecovered` JSONs | 549 |
| Fully decoded recovered registries | 328 |
| Heuristic recovered registries | 221 |

Current classification: this warning class is understood as valid Unity managed-reference data using slash-separated nested class names. The exporter now recovers the registry instead of leaving partial MonoBehaviour JSON.

## 2026-06-29 Structured AB vs AnimeStudio VFSFile Transform

Follow-up on why many structured `.ab` files do not start with `UnityFS` even though AnimeStudio can parse their assets.

Current finding: structured `.ab` files from the VFS dump are raw Endfield VFS file slices after VFS range extraction and optional per-file ChaCha20, but before AnimeStudio's legacy `VFSFile` transform. They are not expected to all start with `UnityFS` on disk.

Relevant code paths:

- Structured dump: `EndfieldVfsLoader.ExtractFile` copies the VFS range and only applies per-file ChaCha20 when the VFS entry has `UseEncrypt`; `EndfieldVfsCli.ProcessDumpFile` writes those bytes directly for bundle-like blocks.
- Asset parse: `FileReader.CheckFileType` recognizes these opaque bytes with `VFSUtils.IsValidHeader`; `AssetsManager.LoadGameBlockFile` dispatches them to `VFSFile`; `VFSFile` then reads the VFS header, decrypts block metadata/data with `VFSAES`, decompresses LZ4 blocks, and emits inner streams for normal Unity parsing.

Byte evidence for `export_full/structured/StreamingAssets/Data/Bundles/Windows/main/a53af5bd74e329b80f12a7f4.ab`:

| Field | Value |
| --- | --- |
| Structured file length | `1626` |
| First 16 bytes | `33 AE CC 8E CD 4C 02 C7 DD 0C 2C B2 F9 0C 2C B2` |
| VFS block | `Bundle` |
| Source chunk | `7064D8E2/68B3B9B8EB82E88FBFE6A313E6B18FB6.chk` |
| Source offset/length | `0` / `1626` |
| VFS encrypted flag | `false` |
| Raw equality | structured file equals source chunk range byte-for-byte |

Current gap: the wrapper currently builds a lightweight VFS index for `Bundle` only, while asset maps include `0CE8FA57` / `InitBundle` sources as well. Next durable VFS work should add an `InitBundle` index and, if needed, a small diagnostic mode around `VFSFile.ReadFiles` to log emitted inner-stream hashes and first bytes for raw-vs-post-transform comparison.

## 2026-06-29 InitBundle VFS Index Coverage

Follow-up on the structured `.ab` / VFSFile transform investigation. Asset maps reference both the normal bundle block (`7064D8E2` / `Bundle`) and initial bundle block (`0CE8FA57` / `InitBundle`), but the wrapper's lightweight VFS index previously summarized only `Bundle`.

Implemented in `scripts/export_full_from_game.py`:

- VFS index generation now covers both `bundle` and `initial-bundle` for each selected source.
- Index files remain per block under `export_full/recovered/AnimeStudio-cli/<source>/vfs_index/`:
  - `bundle_vfs_index.json`
  - `initial-bundle_vfs_index.json`
- The report summary keeps aggregate source-level counts for compatibility and adds a nested `blocks` map with per-block counts and paths.
- Markdown reports now show both per-source aggregate VFS counts and per-block details.

Validation commands:

```bat
python -m py_compile scripts\export_full_from_game.py
AnimeStudio.CLI.exe vfs-index -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -o export_full\recovered\AnimeStudio-cli\StreamingAssets\vfs_index\initial-bundle_vfs_index.json -b initial-bundle
AnimeStudio.CLI.exe vfs-index -s "D:\Program Files\Endfield Game\Endfield_Data\Persistent" -o export_full\recovered\AnimeStudio-cli\Persistent\vfs_index\initial-bundle_vfs_index.json -b initial-bundle --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets"
python scripts\export_full_from_game.py --report-only --skip-structured --animestudio-scope assets --animestudio-stages maps --sources StreamingAssets Persistent --animestudio-jobs 2
```

Fresh report-only run: `reports/20260629_023642`, command failures `0`.

| Source | Block | Files | Chunks | Bytes | Missing chunks |
| --- | --- | ---: | ---: | ---: | ---: |
| StreamingAssets | `bundle` | 257,434 | 31 | 33,313,467,140 | 0 |
| StreamingAssets | `initial-bundle` | 988 | 1 | 237,016,785 | 0 |
| StreamingAssets | aggregate | 258,422 | 32 | 33,550,483,925 | 0 |
| Persistent | `bundle` | 260,697 | 32 | 33,599,451,919 | 0 |
| Persistent | `initial-bundle` | 988 | 1 | 237,022,765 | 0 |
| Persistent | aggregate | 261,685 | 33 | 33,836,474,684 | 0 |

Current classification: lightweight VFS metadata coverage now includes the `InitBundle` block that asset maps already reference. The structured `.ab` files remain classified as raw VFSFile slices before the legacy `VFSFile` decrypt/decompress transform, not as missing UnityFS bundle data.

## 2026-06-29 Nested ManagedReference Payload Decoders

Follow-up on the 221 managed-reference registry recoveries after slash-class support. Subagents checked both raw sidecars and IL2CPP metadata. The slash class names are Unity's serialized nested-type form:

```text
Unity registry: Beyond.Gameplay.AI NpcRabbitGraph/NpcRabbitGraphData Gameplay.Beyond
IL2CPP type:    Beyond.Gameplay.AI.NpcRabbitGraph+NpcRabbitGraphData
```

The exact field lists came from `Endfield_Data/il2cpp_data/Metadata/global-metadata.dat` and matched raw sidecar byte layouts. `tools/DummyDll` was not sufficient for these exact nested definitions.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Full decoder for `Beyond.Gameplay.WeaponWallDisplayConfig/WeaponDisplayConfig`.
  - Layout is `weaponAppearEffectName[3]` followed by `weaponDisappearEffectName[3]`.
- Full decoders for the raw-proven AI nested managed-reference payloads:
  - `EnemyAttackBuildingGraph/EnemyAttackBuildingGraphDatta`
  - `NPCCoilbstEscapeBehavior/NPCCoilbstEscapeBehaviorData`
  - `NpcHideBehavior/NpcHideBehaviorData`
  - `NpcRandomWalkBehavior/NpcRandomWalkBehaviorData`
  - `NpcRabbitGraph/NpcRabbitGraphData`
  - `NpcBornBehavior/NpcBornBehaviorData`
- Remaining heuristic payloads now include bounded `heuristicRawWordHints` so future schema work can compare raw words directly from JSON instead of reopening raw sidecars.

Validation used an isolated CLI build because an unrelated `scripts/build_audio.py --language CN` process was holding the normal release `AnimeStudio.dll`:

```bat
dotnet build tools\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release -f net9.0-windows --no-restore -p:OutDir=D:\fluffy-dump\tmp\animestudio_cli_probe_build\
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_probe_20260629_weapon_ai_nomap --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_probe_after_slash_20260629_022702\filter.json
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_weapon_ai --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Small-probe result:

- `WeaponWallDisplayConfig`: `managedReferencesRegistryFullyDecoded=true`, all 5 refs decoded with appear/disappear effect-name arrays.
- `BB_npc_coilbst_base`: `managedReferencesRegistryFullyDecoded=true`, all 5 NPC behavior/graph refs decoded.
- `BB_eny_0107_wgshoal2_hdg20`: `EnemyAttackBuildingGraphDatta` decoded; `EnemyBattleGraphData` remains heuristic with string/raw-word hints.

221-case before/after:

| Metric | Before | After |
| --- | ---: | ---: |
| Exported JSONs | 15,014 | 15,014 |
| CLI warning/error lines | 0 | 0 |
| Recovered registries | 549 | 549 |
| Fully decoded recovered registries | 328 | 333 |
| Heuristic recovered registries | 221 | 216 |
| Decoded nested refs | 0 | 157 |
| `$unparsed` refs | 865 | 708 |

Resolved `$unparsed` classes in the 221-case probe:

| Class | Count resolved |
| --- | ---: |
| `EnemyAttackBuildingGraph/EnemyAttackBuildingGraphDatta` | 104 |
| `WeaponWallDisplayConfig/WeaponDisplayConfig` | 5 |
| `NPCCoilbstEscapeBehavior/NPCCoilbstEscapeBehaviorData` | 5 |
| `NpcHideBehavior/NpcHideBehaviorData` | 11 |
| `NpcRandomWalkBehavior/NpcRandomWalkBehaviorData` | 13 |
| `NpcRabbitGraph/NpcRabbitGraphData` | 7 |
| `NpcBornBehavior/NpcBornBehaviorData` | 12 |

Top remaining unresolved classes:

| Class | Remaining `$unparsed` refs | Known gap |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | Base fields are known, but longer `enemySR` tails need raw-sidecar proof before claiming full decode. |
| `LuaReference/RefExtraInfo` | 58 | Looks like compact arrays of PPtr-like words; needs IL2CPP field type expansion. |
| `ModelViewStateControllerBase/AnimationParamChangePack` | 54 | String + enum/scalar tail is visible; field names need metadata confirmation. |
| `UILevelMapCrane/CraneSpritePath` | 48 | Looks like a single aligned string path; low-risk next decoder after metadata confirmation. |

Current classification: this batch decodes 157 previously heuristic nested managed-reference payloads using raw byte evidence plus IL2CPP field metadata. It does not mark `EnemyBattleGraphData` fully understood yet because the variable `enemySR` tail is still not proven across all length variants.

## 2026-06-29 UILevelMapCrane ManagedReference Decoder

Follow-up small decoder pass while broader IL2CPP metadata investigation continues. The remaining `Beyond.UI.UILevelMapCrane/CraneSpritePath` refs were low-risk because all 48 heuristic payloads were 12 bytes and decoded as exactly one aligned string:

| Value | Count |
| --- | ---: |
| `crane_1` | 16 |
| `crane_2` | 16 |
| `crane_3` | 16 |

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Full decoder for `UI.Gameplay.Beyond` / `Beyond.UI` / `UILevelMapCrane/CraneSpritePath`.
- Output field: `spritePath`.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_ui_crane --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

The probe emitted 15,014 JSON files with exit code 0 and no warning/error lines.

| Metric | Before UI decoder | After UI decoder |
| --- | ---: | ---: |
| Recovered registries | 549 | 549 |
| Fully decoded recovered registries | 333 | 341 |
| Heuristic recovered registries | 216 | 208 |
| Decoded nested refs | 157 | 205 |
| `$unparsed` refs | 708 | 660 |

Current classification: `UILevelMapCrane/CraneSpritePath` is now fully decoded for the 221-case corpus. Remaining high-count unresolved classes are still `EnemyBattleGraphData`, `LuaReference/RefExtraInfo`, and `ModelViewStateControllerBase/AnimationParamChangePack`.

## 2026-06-29 Remaining ManagedReference Metadata Triage

Follow-up after the UILevelMapCrane decoder. A metadata explorer queried `Endfield_Data/il2cpp_data/Metadata/global-metadata.dat` through the repo-local IL2CPP metadata parser. Metadata file properties reported by the explorer:

| Field | Value |
| --- | --- |
| Version | 29 |
| Size | 58,618,724 bytes |
| SHA-256 | `cf822277f316021dabdce1f21249a01d016e411cea08daf7daa49973e54cc2df` |

Confirmed mapping rule: Unity serialized managed-reference class names use slash-separated nested types, while IL2CPP metadata uses `+` nested names.

| Unity registry class | IL2CPP type |
| --- | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | `Beyond.Gameplay.AI.EnemyBattleGraph+EnemyBattleGraphData` |
| `LuaReference/RefExtraInfo` | `Beyond.Lua.LuaReference+RefExtraInfo` |
| `UILevelMapCrane/CraneSpritePath` | `Beyond.UI.UILevelMapCrane+CraneSpritePath` |

`EnemyBattleGraph/EnemyBattleGraphData` metadata field names:

| Field | Current confidence |
| --- | --- |
| `canvasGraph` | Type index unresolved; do not full-decode yet. |
| `entityMode` | Type index unresolved; do not assume enum/class yet. |
| `soundName` | String, high confidence. |
| `alertRange` | Float, high confidence. |
| `setWaitTime` | Bool/UInt8, high confidence. |
| `waitTime` | Float, high confidence. |
| `useCommonBehavior` | Bool/UInt8, high confidence. |
| `enterConfrontDis` | Float, high confidence. |
| `enemySR` | Tail type unresolved; this is the main blocker. |

Current decision: hold a full `EnemyBattleGraphData` decoder. A partial prefix decoder would be possible, especially for 68-byte baseline payloads, but it would still be partial/heuristic because `canvasGraph`, `entityMode`, and `enemySR` are not fully typed.

`EnemyBattleEventStimulus/EnemyBattleEventStimulusData` metadata field names:

| Field | Current confidence |
| --- | --- |
| `eventType` | Unresolved enum/id. |
| `buffId` | String. |
| `filterDamageDecorate` | Bool/UInt8. |
| `checkType` | Nested enum; names observed: `Exact`, `HasAny`, `HasAll`, `ExceptAny`, `ExceptAll`. |
| `damageDecorateMask` | Numeric mask; exact signedness unresolved. |

Current decision: likely decodable with conservative enum/numeric wrappers, but not promoted yet because `eventType` and mask signedness still need type-index expansion.

`LuaReference/RefExtraInfo` metadata field names:

| Type | Field | Current confidence |
| --- | --- | --- |
| `LuaReference` | `refDict` | TypeTree shows keys `string`, values `PPtr<Component>`. |
| `LuaReference` | `refExtraInfoDict` | TypeTree shows `SerializeReferenceDictionary<string, RefExtraInfo>`. |
| `LuaReference` | `isRootRef` | Bool/UInt8. |
| `LuaReference` | `subReferences` | TypeTree shows `PPtr<LuaReference>` vector. |
| `LuaReference` | `m_table` | Unresolved and not visible in sampled serialized TypeTree. |
| `RefExtraInfo` | `customUIStyles` | Container type unresolved. |
| `CustomUIStyleInfo` | `style` | Type unresolved. |
| `CustomUIStyleInfo` | `component` | Type unresolved. |

Current decision: hold a full `RefExtraInfo` decoder. Raw JSON shows a very regular payload structure, but semantic field typing requires expanding the inner `customUIStyles` type.

`UILevelMapCrane/CraneSpritePath` metadata field name confirmed:

| Field | Type |
| --- | --- |
| `stateSpritePath` | String |

Implementation note: the current exporter output field is `spritePath`, chosen from the raw-value role and class name before metadata confirmation. If stricter metadata naming is preferred later, rename to `stateSpritePath` or include both while preserving compatibility.

Current classification: after the latest decoder work, the remaining high-count managed-reference gaps are not blocked by slash-name parsing anymore. They are schema-completion tasks: expand unresolved IL2CPP type indices, then add targeted decoders only where field names and byte layout agree.

## 2026-06-29 View Animation And Battle Stimulus ManagedReference Decoders

Follow-up decoder pass from the 221-case managed-reference corpus after `UILevelMapCrane/CraneSpritePath` was resolved.

Evidence used:

- IL2CPP metadata from `Endfield_Data/il2cpp_data/Metadata/global-metadata.dat` via `tools/endfield-il2cpp/catalog_option_flow_metadata.py`.
- Current probe JSON from `tmp/monobehaviour_decoder_221_after_ui_crane/MonoBehaviour` using `heuristicRawWordHints`, `heuristicStringHints`, and `heuristicRidLinks`.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `Beyond.Gameplay.View.ModelViewStateControllerBase/AnimationParamChangePack`
  - Fields: `useNewMVSC`, `paramName`, `paramType`, `boolValue`, `floatValue`, `intValue`.
  - `paramType` names are emitted for the observed enum values: `Float`, `Int`, `Bool`, `Trigger`.
- `Beyond.Gameplay.View.ModelViewStateControllerBase/AnimationPackSetState`
  - Fields: `stateName`, `layer`, `normalizedTime`.
- `Beyond.Gameplay.AI.EnemyBattleEventStimulus/EnemyBattleEventStimulusData`
  - Fields: `eventType`, `buffId`, `filterDamageDecorate`, `checkType`, `damageDecorateMask`.
  - `eventType` is preserved as numeric+hex because the enum/id type is not fully resolved yet.
  - `checkType` names are emitted for the nested enum: `Exact`, `HasAny`, `HasAll`, `ExceptAny`, `ExceptAll`.
  - `damageDecorateMask` is decoded as a 64-bit numeric+hex value, matching the raw payload length and `DamageDecorateMask` metadata.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_view_event --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Build result: success with `0` errors. The build reported existing project warnings and transient copy-retry warnings from a short-lived `AnimeStudio.CLI` process, but completed successfully. The targeted export emitted 15,014 JSON files with exit code 0 and no warning/error lines.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| Recovered registries | 549 | 549 |
| Fully decoded recovered registries | 341 | 352 |
| Heuristic recovered registries | 208 | 197 |
| Decoded nested refs | 205 | 296 |
| `$unparsed` refs | 660 | 569 |

Resolved `$unparsed` classes in this pass:

| Class | Count resolved |
| --- | ---: |
| `ModelViewStateControllerBase/AnimationParamChangePack` | 54 |
| `ModelViewStateControllerBase/AnimationPackSetState` | 10 |
| `EnemyBattleEventStimulus/EnemyBattleEventStimulusData` | 27 |

Top remaining unresolved classes after this pass:

| Class | Remaining `$unparsed` refs | Current blocker |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | `canvasGraph`, `entityMode`, and `enemySR` tail type are still not fully resolved. |
| `LuaReference/RefExtraInfo` | 58 | `customUIStyles` container and `CustomUIStyleInfo` member types are not fully expanded. |
| `EnemySettlementBattleBehavior/EnemySettlementBattleBehaviorData` | 24 | Exact nested data field list still needs metadata capture. |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 | Exact nested data field list still needs metadata capture. |
| `EnemyCastSkillResponse/EnemyCastSkillResponseData` | 23 | Looks simple from raw bytes but still needs metadata-backed field names. |

Current classification: these 91 payloads are now schema-decoded from metadata-backed field names and raw byte layouts. Remaining high-count entries are schema-completion work, not parser-warning suppression.

## 2026-06-29 Additional AI ManagedReference Decoders

Follow-up decoder pass after the view animation and battle stimulus work. This pass targeted remaining AI behavior/response payloads where IL2CPP field names and the raw 221-case payload layouts agreed.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `Beyond.Gameplay.AI.EnemyCastSkillResponse/EnemyCastSkillResponseData`
  - Fields: `baseInterval`, `skillId`, `skillTarget`, `interruptSkill`.
  - `skillTarget` enum names emitted: `None`, `Source`, `Self`, `Target`, `MainChar`.
- `Beyond.Gameplay.AI.EnemyCheckBuffStackNum/EnemyCheckBuffStackNumData`
  - Fields: `buffId`, `compareType`, `layerCount`.
  - `compareType` is preserved as numeric+hex because the concrete enum names are not resolved yet.
- `Beyond.Gameplay.AI.NpcFindMainCharBehavior/NpcFindMainCharBehaviorData`
  - Fields: `baseInterval`, `radius`, `angle`, `height`.
- `Beyond.Gameplay.AI.NpcFocusBehavior/NpcFocusBehaviorData`
  - Fields: `baseInterval`, `focusBehavior`.
  - `focusBehavior` is preserved as numeric+hex because the concrete enum names are not resolved yet.
- `Beyond.Gameplay.AI.CharacterFocusBehavior/CharacterFocusBehaviorData`
  - Fields: `baseInterval`, `focusBehavior`, `focusTarget`, `autoLock`, `focusInDis`, `focusOutDis`, `focusDuration`, `duration`.
  - `focusTarget` enum names emitted: `MainChar`, `MainCamera`.
- `Beyond.Gameplay.AI.EnemySimpleAttackBehavior/EnemySimpleAttackBehaviorData`
  - Fields: `baseInterval`, `skillId`, `skillRange`.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_ai_small --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Build result: success with `0` errors and the existing project warnings. The targeted export emitted 15,014 JSON files with exit code 0 and no warning/error lines.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| Recovered registries | 549 | 549 |
| Fully decoded recovered registries | 352 | 352 |
| Heuristic recovered registries | 197 | 197 |
| Decoded nested refs | 296 | 370 |
| `$unparsed` refs | 569 | 495 |

Resolved `$unparsed` classes in this pass:

| Class | Count resolved |
| --- | ---: |
| `EnemyCastSkillResponse/EnemyCastSkillResponseData` | 23 |
| `EnemyCheckBuffStackNum/EnemyCheckBuffStackNumData` | 8 |
| `NpcFindMainCharBehavior/NpcFindMainCharBehaviorData` | 9 |
| `NpcFocusBehavior/NpcFocusBehaviorData` | 15 |
| `CharacterFocusBehavior/CharacterFocusBehaviorData` | 11 |
| `EnemySimpleAttackBehavior/EnemySimpleAttackBehaviorData` | 8 |

Top remaining unresolved classes after this pass:

| Class | Remaining `$unparsed` refs | Current blocker |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | `canvasGraph`, `entityMode`, and `enemySR` tail type are still not fully resolved. |
| `LuaReference/RefExtraInfo` | 58 | `customUIStyles` element types are known by field name but not concrete enough for full semantic decode. |
| `EnemySettlementBattleBehavior/EnemySettlementBattleBehaviorData` | 24 | `skillData` container type still needs exact layout validation. |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 | Graph fields and `enemySR` tail still need exact layout validation. |
| `NpcSingleSwitchGraph/NpcSingleSwitchGraphData` | 9 | `behavior` type index unresolved. |
| `EnemyDefendBattleGraph/EnemyDefendBattleGraphData` | 8 | Graph fields and `enemySR` tail still need exact layout validation. |

Current classification: this pass decodes 74 additional managed-reference payloads without suppressing warnings. Remaining work is concentrated in graph/tail containers and Lua custom UI style references.

## 2026-06-29 Small ManagedReference Decoder Batch

Follow-up pass using two parallel read-only investigations: one metadata-oriented and one raw-layout-oriented. This batch only promoted classes where IL2CPP/DummyDll field evidence and the 221-case raw payload shapes agreed.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `Beyond.Lua.LuaReference/RefExtraInfo`
  - Decodes `customUIStyles` as a counted list of `CustomUIStyleInfo` entries.
  - Each entry has `style` and `component` Unity PPtrs.
- `Beyond.Gameplay.BattleMusicConfig/PotentialEnemyRangeConfig/Circle`
  - Field: `radius`.
- `Beyond.Gameplay.BattleMusicConfig/PotentialEnemyRangeConfig/Sector`
  - Fields: `radius`, `angle`.
- `Beyond.Gameplay.InteractiveBehitPerformSetting/FightBehitBase`
  - Fields: `cameraShake`, `stopFrame`, `entityAnim`.
  - Enum names emitted from `EFightBehit`: `Base`, `Normal`, `HighLevel`.
- `Beyond.Gameplay.AI.EnemyResetPoiseResponse/EnemyResetPoiseResponseData`
  - Field: `baseInterval`.
- `Beyond.Gameplay.AI.EnemyCastSkillInRangeBehavior/EnemyCastSkillInRangeBehaviorData`
  - Field: `baseInterval`.
- `Beyond.Gameplay.AI.EnemyCheckCanInterruptCurSkill/EnemyCheckCanInterruptCurSkillData`
  - Confirmed empty payload.
- `Beyond.Gameplay.AI.EnemyFindTargetlBehavior/EnemyFindTargetlBehaviorData`
  - Fields: `baseInterval`, `forgetTime`.
- `Beyond.Gameplay.AI.EnemyHpChangeStimulus/EnemyHpChangeStimulusData`
  - Fields: `checkType`, `hpPct`.
  - `checkType` names emitted from `Beyond.CompareType`: `LT`, `LE`, `GT`, `GE`, `Equals`.
- `Beyond.Gameplay.AI.EnemyCheckHP/EnemyCheckHPData`
  - Fields: `targetType`, `checkType`, `hpPct`.
  - Target enum names: `Self`, `Source`.
- `Beyond.Gameplay.AI.EnemyCheckInZeroPoise/EnemyCheckInZeroPoiseData`
  - Field: `invert`.
- `Beyond.Gameplay.AI.EnemySinglePatrolBehavior/EnemySinglePatrolBehaviorData`
  - Fields: `baseInterval`, `enterRestart`, `moveMode`, `reachDis`, `reachRunDis`, `entityModeId`, `entityRunModeId`.
  - `moveMode` names emitted: `NavMesh`, `World`, `TowerDefence`.
- `Beyond.Gameplay.AI.EnemySettlementBattleBehavior/EnemySettlementBattleBehaviorData`
  - Fields: `baseInterval`, `skillData`.
  - `skillData` decodes a target-type key list and matching `skillId`/`skillRange` entries.
- `Beyond.Gameplay.AI.NpcSpaceShipBehavior/NpcSpaceShipBehaviorData`
  - Fields: `baseInterval`, `canvasGraph`, `greetVirtualTag`, `greetCD`.
- `Beyond.Gameplay.AI.CharacterSingleSwitchGraph/CharacterSingleSwitchGraphData`
- `Beyond.Gameplay.AI.EnemySingleSwitchGraph/EnemySingleSwitchGraphData`
- `Beyond.Gameplay.AI.NpcSingleSwitchGraph/NpcSingleSwitchGraphData`
  - Fields: `baseInterval`, `behavior` gameplay tag.
- `Beyond.Gameplay.AI.CharacterCheckBehavior/CharacterCheckBehaviorData`
  - Fields: `checkBehaviorType`, `charBehaviorTags`.
  - `charBehaviorTags` is a counted list of `invert` plus behavior gameplay tag.
- `Beyond.Gameplay.AI.EnemyCheckGameplayTag/EnemyCheckGameplayTagData`
  - Fields: `targetType`, `checkTagType`, `tagInfo`.
  - `tagInfo` is a counted list of `invert` plus gameplay tag.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_small_batch --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Build result: success with `0` errors and existing project warnings. The targeted export emitted 15,014 JSON files with exit code 0 and no warning/error lines.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| Recovered registries | 549 | 549 |
| Fully decoded recovered registries | 352 | 371 |
| Not fully decoded recovered registries | 197 | 178 |
| `$unparsed` refs | 495 | 325 |
| `$unparsed` classes | 145 | 126 |

Resolved `$unparsed` classes in this pass:

| Class | Count resolved |
| --- | ---: |
| `LuaReference/RefExtraInfo` | 58 |
| `EnemySettlementBattleBehavior/EnemySettlementBattleBehaviorData` | 24 |
| `NpcSingleSwitchGraph/NpcSingleSwitchGraphData` | 9 |
| `InteractiveBehitPerformSetting/FightBehitBase` | 8 |
| `EnemyResetPoiseResponse/EnemyResetPoiseResponseData` | 7 |
| `EnemySinglePatrolBehavior/EnemySinglePatrolBehaviorData` | 7 |
| `EnemyFindTargetlBehavior/EnemyFindTargetlBehaviorData` | 7 |
| `NpcSpaceShipBehavior/NpcSpaceShipBehaviorData` | 6 |
| `CharacterSingleSwitchGraph/CharacterSingleSwitchGraphData` | 5 |
| `CharacterCheckBehavior/CharacterCheckBehaviorData` | 5 |
| `EnemyHpChangeStimulus/EnemyHpChangeStimulusData` | 5 |
| `EnemyCheckGameplayTag/EnemyCheckGameplayTagData` | 5 |
| `EnemyCastSkillInRangeBehavior/EnemyCastSkillInRangeBehaviorData` | 5 |
| `EnemyCheckInZeroPoise/EnemyCheckInZeroPoiseData` | 4 |
| `EnemyCheckCanInterruptCurSkill/EnemyCheckCanInterruptCurSkillData` | 4 |
| `EnemyCheckHP/EnemyCheckHPData` | 4 |
| `BattleMusicConfig/PotentialEnemyRangeConfig/Sector` | 3 |
| `EnemySingleSwitchGraph/EnemySingleSwitchGraphData` | 3 |
| `BattleMusicConfig/PotentialEnemyRangeConfig/Circle` | 1 |

Top remaining unresolved classes after this pass:

| Class | Remaining `$unparsed` refs | Current blocker |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | Fixed prefix is understood, but optional tail groups include variable rid links and sentinel rid values; list boundaries and semantics are not proven. |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 | Prefix fields are understood, but the optional tail starts after the fixed graph fields and needs list/rid semantics before full decode. |
| `EnemyDefendBattleGraph/EnemyDefendBattleGraphData` | 8 | Raw layout is structurally stable, but field names for several scalar/tail words are still not reliable enough to mark fully decoded. |
| `NpcCommonAnimalGraph/NpcCommonAnimalGraphData` | 5 | Multi-tag graph payload; needs exact metadata-to-byte layout validation. |
| `NpcIdleBehavior/NpcIdleBehaviorData` | 4 | Small payload, likely base interval only, but not yet metadata-confirmed in this pass. |

Current classification: this pass decodes 170 additional managed-reference payloads without suppressing warnings. The highest remaining risk is graph tail reconstruction, not encrypted or missing bundle data.

## 2026-06-29 Second Small AI ManagedReference Batch

Follow-up pass after the small managed-reference decoder batch. This pass targeted the next tier of low-count AI payloads where local IL2CPP metadata and the 221-case raw payload shapes agreed. It deliberately did not promote graph-tail classes.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Base-interval-only payloads:
  - `NpcIdleBehavior/NpcIdleBehaviorData`
  - `NpcPatrolBehavior/NpcPatrolBehaviorData`
  - `CharacterNormalFollowBehavior/CharacterNormalFollowBehaviorData`
  - `CharacterDummyBehavior/CharacterDummyBehaviorData`
  - `CharacterWaitToCloseToHealTargetResponse/CharacterWaitToCloseToHealTargetResponseData`
  - `CharacterIdleSpBehavior/CharacterIdleSpBehaviorData`
  - `CharacterCooperateGraph/CharacterCooperateGraphData`
  - `CharacterTeleportBehavior/CharacterTeleportBehaviorData`
  - `CharacterMainBehavior/CharacterMainBehaviorData`
  - `EnemyImmobilizedBehavior/EnemyImmobilizedBehaviorData`
  - `EnemyBattleIdleBehavior/EnemyBattleIdleBehaviorData`
  - `EnemySimpleCastSequenceSkillBehavior/EnemySimpleCastSequenceSkillBehaviorData`
  - `EnemyPauseBehavior/EnemyPauseBehaviorData`
  - `EnemyCastSequenceSkillBehavior/EnemyCastSequenceSkillBehaviorData`
  - `NpcIdleShowBehavior/NpcIdleShowBehaviorData`
- Confirmed empty payloads:
  - `CharacterCloseToHealTargetStimulus/CharacterCloseToHealTargetStimulusData`
  - `CharacterHealTargetStimulus/CharacterHealTargetStimulusData`
- Metadata-backed fields:
  - `CharacterIdleBehavior/CharacterIdleBehaviorData`: `baseInterval`, `stopMove`.
  - `NpcBirdIdleBehavior/NpcBirdIdleBehaviorData`: `baseInterval`, `searchRadius`.
  - `CharacterCheckNeedDodgeAlert/CharacterCheckNeedDodgeAlertData`: `invert`.
  - `CharacterStayOutOfViewBehavior/CharacterStayOutOfViewBehaviorData`: `baseInterval`, `mode`, `step`, `tryCount`, `dis`, `xRange`, `yRange`.
  - `CharacterSwitchFollowStateResponse/CharacterSwitchFollowStateResponseData`: `baseInterval`, `state` numeric+hex.
  - `EnemyLeaveBattleBehavior/EnemyLeaveBattleBehaviorData`: `baseInterval`, `animName`, `waitTime`.
  - `EnemyGroupPatrolBehavior/EnemyGroupPatrolBehaviorData`: `baseInterval`, `clampRatio`.
  - `EnemyCommonStimulus/EnemyCommonStimulusData`: `stimulusType` numeric+hex.
  - `EnemyCheckAngleToSource/EnemyCheckAngleToSourceData`: `revert`, `angle`.
  - `EnemyCheckAIMarker/EnemyCheckAIMarkerData`: `checkMarkerType`, counted `markerInfo` list.
  - `EnemyFormationMoveBehavior/EnemyFormationMoveBehaviorData`: `baseInterval`, `timeout`, `soundName`, `delayEnd`.
  - `EnemyConfrontMoveBehavior/EnemyConfrontMoveBehaviorData`: `baseInterval`, `timeout`.
  - `CharacterWaitBehavior/CharacterWaitBehaviorData`: `baseInterval`, `exitDis`.
  - `CharacterCastSkillBehavior/CharacterCastSkillBehaviorData`: `baseInterval`, `duration`.
  - `CharacterIdleDodgeBehavior/CharacterIdleDodgeBehaviorData`: `baseInterval`, `duration`.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_small_ai2 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Build result: success with `0` errors and existing project warnings. The targeted export emitted 15,014 JSON files with exit code 0 and no warning/error lines.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| Recovered registries | 549 | 549 |
| Fully decoded recovered registries | 371 | 372 |
| Not fully decoded recovered registries | 178 | 177 |
| `$unparsed` refs | 325 | 262 |
| `$unparsed` classes | 126 | 94 |

This pass resolved 63 additional `$unparsed` managed-reference payloads. Largest remaining blockers after this pass:

| Class | Remaining `$unparsed` refs | Current blocker |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | Variable graph tail with rid links/sentinel rids; fixed prefix is not enough for full decode. |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 | Fixed prefix is known, optional tail list semantics remain unresolved. |
| `EnemyDefendBattleGraph/EnemyDefendBattleGraphData` | 8 | Structurally stable small graph payload, but several scalar/tail field names still need stronger evidence. |
| `NpcCommonAnimalGraph/NpcCommonAnimalGraphData` | 5 | Multi-tag graph payload needs exact metadata-to-byte validation. |
| `EnemyDodgeResponse/EnemyDodgeResponseData` | 3 | Multi-string response payload; metadata field order still needs confirmation. |
| `EnemyCheckTag/EnemyCheckTagData` | 3 | Looks like counted/inverted tag data, but enum/container field names still need confirmation. |

Current classification: this pass decodes low-risk AI behavior data and leaves the remaining hard problem concentrated in graph-tail/list reconstruction.

## 2026-06-29 Third Small AI and NPC Graph ManagedReference Batch

Follow-up pass after `tmp\monobehaviour_decoder_221_after_small_ai2`. Two read-only subagents split the remaining inventory: one checked low-count non-graph AI/view payloads, and one checked graph payloads. This pass only promoted layouts where the payload can be consumed completely with metadata-backed fields. It deliberately did not promote enemy battle graph prefix-only decoders, because `enemySR` tail semantics are still unresolved.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Low-count AI behavior/stimulus payloads:
  - `EnemyDodgeResponse/EnemyDodgeResponseData`: `baseInterval`, `nearDis`, counted `nearSkill`, counted `farSkill`.
  - `EnemyPlaySoundBehavior/EnemyPlaySoundBehaviorData`: `baseInterval`, `soundName`, `radius`, `loop`, `interval`.
  - `NpcBirdFlyBehavior/NpcBirdFlyBehaviorData`: movement sampling floats/ints plus `flyStartAnim` gameplay tag.
  - `NpcCommonStimulus/NpcCommonStimulusData`: `stimulusType` numeric+hex.
  - `NpcCheckBehavior/NpcCheckBehaviorData`: `checkBehaviorType`, counted inverted gameplay-tag list.
  - `NPCRabbitEscapeBehavior/NPCRabbitEscapeBehaviorData`: escape timing/range fields plus `escapeMontageTag`.
  - `NpcSlugToRigBodyBehavior/NpcSlugToRigBodyBehaviorData`: rigidbody object/string, two vectors, montage tag.
  - `NpcShrivelledBehavior/NpcShrivelledBehaviorData`: `shrivelledAnim`, `dropItemTag` gameplay tags.
  - `CharacterPatrolBehavior/CharacterPatrolBehaviorData`: `baseInterval`, reach distances.
  - `CharacterBattleActionStimulus/CharacterBattleActionStimulusData`: `eventType` numeric+hex.
  - `CharacterCheckDodge/CharacterCheckDodgeData`: `dodgeProp` numeric+hex.
  - `CharacterCommonStimulus/CharacterCommonStimulusData`: `stimulusType` numeric+hex.
  - `CharacterDodgeResponse/CharacterDodgeResponseData`: `baseInterval`, `dodgeCD`.
  - `CharacterCloseToHealTargetBehavior/CharacterCloseToHealTargetBehaviorData`: `baseInterval`, timeout, stop distance.
  - `CharacterFarmingFollowBehavior/CharacterFarmingFollowBehaviorData`: `baseInterval`, `duration`.
  - `CharacterNormalBattleBehavior/CharacterNormalBattleBehaviorData`: `baseInterval` plus seven metadata-backed floats.
  - `CharacterSwitchBehaviorResponse/CharacterSwitchBehaviorResponseData`: `baseInterval`, `behavior` gameplay tag.
  - `EnemyCheckStringParam/EnemyCheckStringParamData`: `stringValue`.
- Trivial AI payloads:
  - Base-interval only: `CharacterBattleJumpBehavior`, `CharacterForceTeleportBehavior`, `CharacterJumpResponse`, `CharacterSkillHoldBehavior` data classes.
  - Empty: `CharacterJumpStimulus/CharacterJumpStimulusData`.
- Fully consumed NPC graph payloads:
  - `NpcCommonAnimalGraph/NpcCommonAnimalGraphData`: born/idle/escape/hide tags and escape/hide scalar fields.
  - `NpcBirdGraph/NpcBirdGraphData`: born/idle/fly/hide tags.
  - `NpcSnailGraph/NpcSnailGraphData`: shrivelled/free-walk tags.
- View animation payload:
  - `WeaponAnimatorMono/PlayFollowEffect`: `effectName`, `restartIfExist`, `mountPoint` numeric+hex.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_small_ai3_fullnpc --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Build result: success with `0` warnings and `0` errors after the final formatting cleanup. The targeted export emitted 15,014 JSON files with exit code 0 and no warning/error lines.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| JSON files emitted | 15,014 | 15,014 |
| `$unparsed` refs | 262 | 216 |
| `$unparsed` classes | 94 | 67 |

Resolved `$unparsed` payloads in this pass: 46.

Largest remaining blockers after this pass:

| Class | Remaining `$unparsed` refs | Current blocker |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | Fixed prefix is mapped, but `enemySR` tail grouping, rid links, sentinel rid values, and exact semantics are not proven. |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 | Fixed prefix is mapped, but `enemySR` tail/list semantics and `exAction` type are not proven. |
| `EnemyDefendBattleGraph/EnemyDefendBattleGraphData` | 8 | Structurally stable 44-byte payload, but `searchMode` enum/type proof and canonical empty `enemySR` semantics are still pending. |
| `EnemyCheckTag/EnemyCheckTagData` | 3 | `targetType` and `checkTagType` are clear, but `tagInfo` is not the normal gameplay-tag path+hash layout; leaving unresolved avoids a false full decode. |
| Single-count character/AI behavior classes | 1 each | Several include PQS/custom/list structures or missing exact data-class metadata and need separate evidence. |

Current classification: this pass resolves the next low-risk AI/view/NPC graph payloads without suppressing warning semantics. The remaining high-count problem is enemy battle graph tail reconstruction, not missing VFS extraction or repeated encryption.

## 2026-06-29 Fourth Low-Count AI ManagedReference Batch

Follow-up pass after `tmp\monobehaviour_decoder_221_after_small_ai3_fullnpc`. This pass targeted one-off AI/NPC payloads whose local IL2CPP metadata fields and raw byte shapes matched exactly. Enemy graph tails, `EnemyCheckTag`, `NpcDailyGraph`, and `WeaponAnimatorMono/StateActionEntry` stayed unresolved because they require reference-list or custom-container semantics beyond simple full-byte consumption.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Character AI payloads:
  - `CharacterAttackResourceBehavior/CharacterAttackResourceBehaviorData`: `baseInterval`, `attackPQS` PPtr, `timeout`.
  - `CharacterBattleCommandBehavior/CharacterBattleCommandBehaviorData`: `baseInterval`, `safeAreaPQS` PPtr, `reactionDelay` Vector2.
  - `CharacterBarkExploreBehavior/CharacterBarkExploreBehaviorData`: `baseInterval`, `gait` numeric+hex, two talk ids, call distances/timing.
  - `CharacterCheckSpIdle/CharacterCheckSpIdleData`: `revert`.
  - `CharacterFocusImportantBehavior/CharacterFocusImportantBehaviorData`: `baseInterval`, `walkDuration`, `exitRadius`, `returnWalkDuration`.
  - `CharacterFarmGraph/CharacterFarmGraphData`: five gameplay tags.
  - Base-interval-only: `CharacterCastSkillGraph/CharacterCastSkillGraphData`, `CharacterEvadeBehavior/CharacterEvadeBehaviorData`.
- NPC AI payloads:
  - `NpcBattleConfrontBehavior/NpcBattleConfrontBehaviorData`: `animTag`, `needRot`, `randomDelay`.
  - `NpcCleanPackAnimalBehavior/NpcCleanPackAnimalBehaviorData`: `happyAnimTag`.
  - `NpcFecesPackAnimalBehavior/NpcFecesPackAnimalBehaviorData`: perform ids and failed-toast string.
  - `NpcLeaveBattleBehavior/NpcLeaveBattleBehaviorData`: `randomDelay`.
  - `NpcSlugBehavior/NpcSlugBehaviorData`: lie/hit animation tags and duration.
  - `NpcSlugLieBehavior/NpcSlugLieBehaviorData`: lie animation tag.
  - `NpcSlugGraph/NpcSlugGraphData`: idle/patrol/idle-show/slug/slug-lie tags.
  - `NpcSpaceShipGraph/NpcSpaceShipGraphData`: eight spaceship behavior tags.
  - `NpcSpaceShipLeaveBehavior/NpcSpaceShipLeaveBehaviorData`: `greetVirtualTag`, `greetCD`.
  - `NpcSpaceShipWaitBehavior/NpcSpaceShipWaitBehaviorData`: `waitTime` Vector2.
  - Base-interval-only: `NpcAttractBehavior`, `NpcPassiveAttractBehavior`, `NpcBattleConfrontResponse`, `NpcEnvConfrontResponse`, and `NpcSettlementBehavior` data classes.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_small_ai4_moregraphs --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Final build result after formatting cleanup: success with `0` warnings and `0` errors. The targeted export emitted 15,014 JSON files with exit code 0 and no warning/error lines.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| JSON files emitted | 15,014 | 15,014 |
| `$unparsed` refs | 216 | 193 |
| `$unparsed` classes | 67 | 44 |

Resolved `$unparsed` payloads in this pass: 23.

Largest remaining blockers after this pass:

| Class | Remaining `$unparsed` refs | Current blocker |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | Fixed prefix is mapped, but `enemySR` tail grouping, rid links, sentinel rid values, and exact semantics are not proven. |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 | Fixed prefix is mapped, but `enemySR` tail/list semantics and `exAction` type are not proven. |
| `EnemyDefendBattleGraph/EnemyDefendBattleGraphData` | 8 | Structurally stable 44-byte payload, but `searchMode` enum/type proof and canonical empty `enemySR` semantics are still pending. |
| `EnemyCheckTag/EnemyCheckTagData` | 3 | `tagInfo` is a compact numeric list, not the existing gameplay-tag path+hash layout; exact element type is still under investigation. |
| Remaining single-count graph/list classes | 1 each | Most contain rid lists, PQS/custom data, `npcSR`, `enemySR`, or other custom containers that need separate semantics before full decode. |

Current classification: this pass resolves low-count scalar/string/tag payloads and leaves remaining work concentrated in graph/reference-list containers. Two read-only subagents were left investigating `EnemyCheckTag` and enemy graph tails during this pass; their conclusions should be folded into the next batch when available.

## 2026-06-29 Fifth Low-Count AI ManagedReference Batch

Follow-up pass after `tmp\monobehaviour_decoder_221_after_small_ai4_moregraphs`. This pass targeted simple one-off AI behavior payloads with metadata-backed scalar/string/tag layouts and a small base-interval-only group. It deliberately left enemy battle graph tails, `EnemyCheckTag`, remaining custom graph/list containers, Core ability actions, and `WeaponAnimatorMono/StateActionEntry` unresolved until their list/reference semantics are proven.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Character AI payloads:
  - `CharacterPickupBehavior/CharacterPickupBehaviorData`: `baseInterval`, `skillId`, `pickupTag`, counted `pickupInteractId`, movement radii/timeouts, and emoji strings.
  - `CharacterRepatriateBehavior/CharacterRepatriateBehaviorData`: `baseInterval`, `performId`, `duration`.
  - `CharacterSeatBehavior/CharacterSeatBehaviorData`: `baseInterval`, stop/walk distances, `performId`, `delay`.
  - `CharacterSettlementBattleBehavior/CharacterSettlementBattleBehaviorData`: `baseInterval`, dodge distance/angle/cooldown.
  - Base-interval-only: `CharacterPlungingAttackBehavior`, `CharacterSummonTeamBehavior`, `CharacterHealTargetBehavior`.
- Enemy AI payloads:
  - `EnemyDogEscapeBehavior/EnemyDogEscapeBehaviorData`: skill/timing/escape distance fields.
  - `EnemyDogGraph/EnemyDogGraphData`: single/group patrol, random-walk, and escape gameplay tags.
  - `EnemyEnvConfrontBehavior/EnemyEnvConfrontBehaviorData`: idle-break min/max timing.
  - `EnemyLeaveBattleGraph/EnemyLeaveBattleGraphData`: leave/teleport gameplay tags.
  - `EnemyMoveToValidPosBehavior/EnemyMoveToValidPosBehaviorData`: radius, stop distance, timeout.
  - `EnemyRandomWalkBehavior/EnemyRandomWalkBehaviorData`: entity mode id, radius/angle, idle-time and distance vectors, try count.
  - `EnemyScriptedMoveGraph/EnemyScriptedMoveGraphData`: enemy/main-character in/out radius/count thresholds.
  - `EnemySetBlackboardResponse/EnemySetBlackboardResponseData`: key/global/value union fields.
  - `EnemyVigilanceBehavior/EnemyVigilanceBehaviorData`: extra wait time.
  - Base-interval-only: `EnemyEnvConfrontResponse`, `EnemyIdleBehavior`, `EnemyLeaveBattleTeleportBehavior`, `EnemyMainCharExceedRange`, `EnemyMoveToOuterRadius`, `EnemyTargetInProximity`.
- NPC AI payloads:
  - `NPCCoilbstSitBehavior/NPCCoilbstSitBehaviorData`: sit/end montage tags, intervals, counted random montage tags, root-motion height.
  - `NPCCommonAnimalEscapeBehavior/NPCCommonAnimalEscapeBehaviorData`: movement style, timing/range fields, play-montage flag, escape montage tag.
  - `NPCCommonAnimalLoopMontageBehavior/NPCCommonAnimalLoopMontageBehaviorData`: loop montage tag and duration.
  - `NPCEnvConfrontBehavior/NPCEnvConfrontBehaviorData`: animation tag, rotation flag, random delay, idle-break timings.
  - `NPCLotusFrogEscapeBehavior/NPCLotusFrogEscapeBehaviorData`: duration, escape montage tag, backward correction.
  - `NPCPlayanimationBehavior/NPCPlayanimationBehaviorData`: animation tag.
  - `NPCPlayanimationHideBehavior/NPCPlayanimationHideBehaviorData`: animation tag and fade time.
  - `NPCResetToBornBehavior/NPCResetToBornBehaviorData`: disappear/appear animation tags.
- Shared helper:
  - `ReadPayloadGameplayTagList` for counted gameplay-tag arrays.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_small_ai5_morelow --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Build result: success with the existing project warnings and `0` errors. The targeted export emitted 15,014 JSON files with exit code 0 and no warning/error lines.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| JSON files emitted | 15,014 | 15,014 |
| `$unparsed` refs | 193 | 163 |
| `$unparsed` classes | 44 | 14 |

Resolved `$unparsed` payloads in this pass: 30.

Remaining blockers after this pass:

| Class | Remaining `$unparsed` refs | Current blocker |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | Fixed prefix is mapped, but `enemySR` tail grouping, rid links, sentinel rid values, and exact semantics are not proven. |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 | Fixed prefix is mapped, but `enemySR` tail/list semantics and `exAction` type are not proven. |
| `EnemyDefendBattleGraph/EnemyDefendBattleGraphData` | 8 | Structurally stable 44-byte payload, but `searchMode` enum/type proof and canonical empty `enemySR` semantics are still pending. |
| `EnemyCheckTag/EnemyCheckTagData` | 3 | `tagInfo` remains a compact numeric/list payload rather than the normal gameplay-tag path+hash layout. |
| One-off graph/list/custom classes | 1 each | `CharacterFollowGraph`, `CharacterBattleGraph`, `CharacterFarmingBehavior`, `EnemyPatrolGraph`, `EnemyBornBehavior`, `NPCCommonAnimalRandomPlayMontageBehavior`, `NpcDailyGraph`, `ShowSquadTipsAction/Data`, `FinishGlobalBuffAction/Data`, and `WeaponAnimatorMono/StateActionEntry` need separate layout proof before full decode. |

Current classification: this pass removes the straightforward low-risk one-off behavior payloads. The unresolved set is now dominated by AI graph/reference-list/custom-container semantics, not missing AB extraction, raw VFS coverage, or repeated encryption.

## 2026-06-29 Sixth Graph-Lite ManagedReference Batch

Follow-up pass after `tmp\monobehaviour_decoder_221_after_small_ai5_morelow`. Two read-only subagents returned evidence during this pass: one resolved `EnemyCheckTag` as a counted `EnemyCheckTagInfo` list whose `query` is `Beyond.Gameplay.PredefinedQuery`, and one confirmed exact byte layouts for several remaining one-count payloads. No subagent edited files.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `EnemyCheckTag/EnemyCheckTagData`: `targetType`, `checkTagType`, and counted `tagInfo` entries of `invert` plus `PredefinedQuery` value. Known value `7` is labeled `InImmobilized`; other values remain numeric+hex until the enum is fully mapped.
- `CharacterFarmingBehavior/CharacterFarmingBehaviorData`: scalar movement/farming thresholds plus `farmInfo` int-to-perform-id dictionary. The `farmInfo` key enum names are not proven, so keys are preserved as raw int/hex values.
- `NpcDailyGraph/NpcDailyGraphData`: five behavior gameplay tags plus counted `npcSR.cfg` entries with RID-linked stimulus, condition-list, and response references.
- `ShowSquadTipsAction/Data`: inherited ability-action prefix (`isEnable`, `priorityLevel`, `priorityOffset`, `serverActionIndex`) plus `textId`.
- `WeaponAnimatorMono/StateActionEntry`: counted RID-linked `actionsOnEnter` and `actionsOnExit` lists.
- Dispatch plumbing now passes the recovered managed-reference RID map into the AI and View decoders, and adds a small Core gameplay decoder path for ability-action data.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_small_ai6_graphlite --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Build result: success with the existing project warnings and `0` errors. The targeted export emitted 15,014 JSON files with exit code 0 and no warning/error lines.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| JSON files emitted | 15,014 | 15,014 |
| `$unparsed` refs | 163 | 156 |
| `$unparsed` classes | 14 | 9 |

Resolved `$unparsed` payloads in this pass: 7.

Remaining blockers after this pass:

| Class | Remaining `$unparsed` refs | Current blocker |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | Fixed prefix is mapped, but `enemySR` tail grouping, rid links, sentinel rid values, and exact semantics are not proven. |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 | Fixed prefix is mapped, but `enemySR` tail/list semantics and `exAction` type are not proven. |
| `EnemyDefendBattleGraph/EnemyDefendBattleGraphData` | 8 | Structurally stable 44-byte payload, but `searchMode` enum/type proof and canonical empty `enemySR` semantics are still pending. |
| One-off graph/custom classes | 1 each | `CharacterFollowGraph`, `CharacterBattleGraph`, `EnemyPatrolGraph`, `EnemyBornBehavior`, `NPCCommonAnimalRandomPlayMontageBehavior`, and `FinishGlobalBuffAction/Data` still need exact custom container or inherited-prefix proof. |

Current classification: repeated encryption and missing VFS extraction are not implicated in the remaining set. The unresolved payloads are now mostly AI graph/reference-list containers plus a few custom inherited data classes.

## 2026-06-29 Seventh One-Off ManagedReference Batch

Follow-up pass after `tmp\monobehaviour_decoder_221_after_small_ai6_graphlite`. This pass targeted the remaining non-graph one-off payloads that had enough metadata and byte-layout evidence to decode without weakening warning semantics.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `NPCCommonAnimalRandomPlayMontageBehavior/NPCCommonAnimalRandomPlayMontageBehaviorData`: `baseInterval`, counted `PlayTimedMontageInfo` entries (`playMontageTag`, `overrideMontageStartState`, `montageStartState`, `limitMaxDuration`, `duration`), and `playInterval`.
- `FinishGlobalBuffAction/Data`: inherited ability-action prefix (`isEnable`, `priorityLevel`, `priorityOffset`, `serverActionIndex`), `finishParent`, counted `globalBuffIds`, `finishAll`, `finishCount` as a `BlackboardDouble`-shaped value (`useBlackboardKey`, scalar value, `blackboardKey`), and `isFinishedEarly`.
- Core gameplay decoder routing now accepts nested `Beyond.Gameplay.Core.*` namespaces so `Beyond.Gameplay.Core.AbilityActions.FinishGlobalBuffAction/Data` reaches the Core decoder.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_small_ai7_finishfix --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Build result: success with the existing project warnings and `0` errors. The targeted export emitted 15,014 JSON files with exit code 0 and no warning/error lines.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| JSON files emitted | 15,014 | 15,014 |
| `$unparsed` refs | 156 | 154 |
| `$unparsed` classes | 9 | 7 |

Resolved `$unparsed` payloads in this pass: 2.

Remaining blockers after this pass:

| Class | Remaining `$unparsed` refs | Current blocker |
| --- | ---: | --- |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 | Fixed prefix is mapped, but `enemySR` tail grouping, rid links, sentinel rid values, and exact semantics are not proven. |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 | Fixed prefix is mapped, but `enemySR` tail/list semantics and `exAction` type are not proven. |
| `EnemyDefendBattleGraph/EnemyDefendBattleGraphData` | 8 | Structurally stable 44-byte payload, but `searchMode` enum/type proof and canonical empty `enemySR` semantics are still pending. |
| One-off graph/custom classes | 1 each | `CharacterFollowGraph`, `CharacterBattleGraph`, `EnemyPatrolGraph`, and `EnemyBornBehavior` still need exact graph/reference-list or born-action semantics before full decode. |

Current classification: the simple scalar/string/tag/list one-offs are exhausted for this 221-case set. Remaining work is concentrated in graph/reference-list semantics and the custom enemy-born action structure.

## 2026-06-29 Eighth AI Graph Decoder Completion Batch

Follow-up pass after `tmp\monobehaviour_decoder_221_after_small_ai7_finishfix`. Three read-only subagents returned exact byte-layout evidence for the remaining character graph, enemy patrol/born, and enemy battle/settlement/defend graph payloads. No subagent edited files.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- `CharacterFollowGraph/CharacterFollowGraphData`: `baseCheckInterval`, `randomCheckInterval`, and `CharacterSR` as an inferred object with an unresolved leading scalar preserved as `unknownFloat0`, plus counted `srData` entries of `finishCount`, `stimulusCfg`, `stimulusConditionCfg`, and `responseCfg` RID links.
- `CharacterBattleGraph/CharacterBattleGraphData`: the same `CharacterSR` object layout.
- `EnemyPatrolGraph/EnemyPatrolGraphData`: `baseInterval`, `singlePatrol`, `groupPatrol`, and counted `enemySR` entries using the same managed-reference RID-link record shape.
- `EnemyBornBehavior/EnemyBornBehaviorData`: `baseInterval` and nested `bornBehaviorData` with aligned string, int32 mode, bool32, and float fields for enter/exit animation and interrupt data.
- `EnemyBattleGraph/EnemyBattleGraphData`: fixed prefix (`baseInterval`, `canvasGraph`, `entityMode`, `soundName`, `alertRange`, wait/common-behavior fields, `enterConfrontDis`) plus counted `enemySR`.
- `EnemyDefendBattleGraph/EnemyDefendBattleGraphData`: fixed prefix (`baseInterval`, `canvasGraph`, common-behavior/search fields, `searchMode`, `onHitTimeout`) plus counted `enemySR`.
- `EnemySettlementBattleGraph/EnemySettlementBattleGraphData`: fixed prefix (`baseInterval`, `canvasGraph`, battle/patrol tags, search/sight/leave fields, `exAction`) plus counted `enemySR`.

Known conservative choices:

- `CharacterSR.unknownFloat0` remains intentionally unnamed; metadata proves the container and `srData` shape, but not that scalar's field name.
- `entityMode`, `searchMode`, `exAction`, and enemy-born enter/exit modes are emitted as raw int32/hash-style values, not guessed enum names.
- Negative managed-reference RID sentinels are preserved through the existing RID-link output instead of being converted into fake references.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\monobehaviour_decoder_221_after_graph_all1 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --filter_data tmp\monobehaviour_warning_221_after_slash\filter.json
```

Build result: success with the existing project warnings and `0` errors. The targeted export emitted 15,014 JSON files with exit code 0. Log grep for `Warning`, `Error`, `metadata-only JSON`, and `Export ... error` returned no matches.

221-case before/after this pass:

| Metric | Before this pass | After this pass |
| --- | ---: | ---: |
| JSON files emitted | 15,014 | 15,014 |
| `$unparsed` refs | 154 | 0 |
| `$unparsed` classes | 7 | 0 |

Resolved `$unparsed` payloads in this pass: 154.

Resolved classes:

| Class | Resolved `$unparsed` refs |
| --- | ---: |
| `EnemyBattleGraph/EnemyBattleGraphData` | 118 |
| `EnemySettlementBattleGraph/EnemySettlementBattleGraphData` | 24 |
| `EnemyDefendBattleGraph/EnemyDefendBattleGraphData` | 8 |
| `CharacterFollowGraph/CharacterFollowGraphData` | 1 |
| `CharacterBattleGraph/CharacterBattleGraphData` | 1 |
| `EnemyPatrolGraph/EnemyPatrolGraphData` | 1 |
| `EnemyBornBehavior/EnemyBornBehaviorData` | 1 |

Current classification: for this focused 221-case MonoBehaviour warning set, AnimeStudio now emits decoded JSON without `$unparsed` managed-reference payloads and without warning/error log lines. This does not prove every asset type in the full installed game export is fully understood; it closes the remaining AI managed-reference layouts from this warning report.

## 2026-06-29 Ninth Fresh StreamingAssets Guide-Condition Batch

Follow-up after the focused 221-case cleanup. A contained fresh StreamingAssets JSON audit was run outside `export_full`:

```bat
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\fresh_json_audit_20260629_streaming --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types TextAsset:Both MonoBehaviour:Both PlayableDirector:Both Material:Both --dummy_dlls tools\DummyDll
```

Fresh audit results:

| Type | JSON files |
| --- | ---: |
| `Material` | 48,490 |
| `MonoBehaviour` | 963,849 |
| `PlayableDirector` | 9,856 |
| `TextAsset` | 6,757 |
| Total | 1,028,952 |

The fresh audit log had no warning/error lines, no metadata-only JSON warnings, no partial-TypeTree warnings, no `Export ... error` lines, and no `Unknown ClassIDType` lines. A byte-level marker scan found remaining MonoBehaviour fallback markers: `$unparsed` in 1,758 files / 11,268 occurrences and `decodeError` in 1,937 files / 1,937 occurrences. This is a broader population than the earlier 221-case filter.

Subagent findings:

- The old `Unknown ClassIDType 1186182244` warning is stale; current code names it `HGCorrectiveBoneData`, and current reports do not contain that warning.
- The `CCS_*` and `data_abilityentity_*` `decodeError` bucket is not encryption. Script-first DummyDll probing did not improve it. The failures are managed-reference TypeTree overreads where numeric/float payload bytes are interpreted as aligned-string lengths; heuristic managed-reference recovery is preserving the payload.
- Current non-MonoBehaviour conversion buckets show no missing outputs or export errors in current status manifests; remaining notable conversion coverage questions are Animator no-mesh markers and deduplicated shared-output references.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added `TryDecodeGuideManagedReferenceData` before the generic Core/AI managed-reference decoders.
- Decoded proven guide/tutorial condition layouts:
  - `Beyond.Gameplay.InMainHud`
  - `Beyond.Gameplay.CombineCondition`
  - `Beyond.Gameplay.CheckMissionState`
  - `Beyond.Gameplay.CheckGuideGroupComplete`
  - `Beyond.Gameplay.Conditions.OnPlayerActionTriggerOnly`
  - `Beyond.Gameplay.Conditions.OnUIPanelOpen`
  - base-only `OnCastUltimateSkill` and `OnCastNormalSkill`
- Added strict helpers for the observed guide condition prefix, string/int/bool parameter wrappers, and bounded aligned ASCII parameter strings. Unknown inherited words remain explicitly named `unknown*` rather than guessed.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\guide_condition_probe_names_after1 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^(guide_battle_enemy_interrupt_ct|guide_blackbox_1_powerpole_ct|guide_activity_snapshot_formation_1_ct|guide_blackbox_1_complete_ct|guide_blackbox_1_furance_ct)$"
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\guide_condition_probe_allguide_after1 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^guide_"
```

Build result: success with `0` warnings and `0` errors. Both validation logs had no warning/error lines.

Guide-only before/after from the fresh audit baseline and the new guide probe:

| Metric | Before | After |
| --- | ---: | ---: |
| Guide JSON files | 1,623 | 1,621 |
| Guide `$unparsed` refs | 8,595 | 5,864 |
| Guide `$unparsed` classes | 348 | 299 |
| Decoded guide refs in probe | 1 | 2,728 |

Decoded target refs in the guide-only probe:

| Class | Decoded refs |
| --- | ---: |
| `CombineCondition` | 628 |
| `InMainHud` | 500 |
| `OnPlayerActionTriggerOnly` | 416 |
| `CheckGuideGroupComplete` | 392 |
| `OnUIPanelOpen` | 389 |
| `CheckMissionState` | 385 |
| `OnCastUltimateSkill` | 9 |
| `OnCastNormalSkill` | 9 |

Remaining guide bucket after this pass is dominated by action layouts, especially camera/factory/HUD guide actions such as `BlendToCameraTransformWithoutBack`, `BlendOutFromCamera`, `GuideUnFreezeWorld`, `RecoverMainHud`, `GuideFreezeWorld`, `FinishEffect`, `FacLockBuildPos`, and `SetFacTopView`. Their shared action prefix is visible, but only tails with proven semantics should be promoted in later passes.

## 2026-06-29 Tenth Fresh StreamingAssets Guide-Action Batch

Follow-up after the ninth guide-condition batch. This pass targeted only guide/tutorial managed-reference actions with both IL2CPP field evidence and stable byte layouts. Camera blends, tracking-point actions, and multi-field factory actions were left untouched unless their tail shape was proven.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Extended `TryDecodeGuideManagedReferenceData` to route `Beyond.Gameplay.Actions` payloads.
- Added a strict 36-byte guide action base decoder: action index/hash, action id, three inherited raw words, mode/group word, and bool32 enabled flag.
- Decoded fixed one-raw-word actions: `RecoverMainHud` and `ExitFacBuildMode`.
- Decoded one-bool guide actions: `DisableHudFade`, `FacLockBuildPos`, `FacSetEnableConfirmBuild`, `FacSetEnableExitBuildMode`, `SetEnablePlayerMove`, `SetEnablePlayerMoveCamera`, `SetFacMode`, `SetFacTopView`, `SetGeneralAbilityReleaseClose`, `ToggleClearScreen`, `ToggleGeneralAbilityClick`, `ToggleGeneralAbilityLoneClick`, and `ToggleQuickMenuReleaseClose`.
- Decoded one-float guide action: `SetAtbValue`.
- Decoded string-tail guide actions: `GuideFreezeWorld`, `GuideUnFreezeWorld`, and `FinishEffect`.
- Kept wrapper/tail words as `unknown*` or raw hash words when metadata does not prove a semantic name.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\guide_action_probe_allguide_after1 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^guide_"
```

Final build result: success with `0` warnings and `0` errors. The guide-only probe emitted 1,621 MonoBehaviour JSON files with exit code 0. Log grep for `Warning`, `Error`, `metadata-only JSON`, partial-TypeTree warnings, `Export ... error`, and `Unknown ClassIDType` returned no matches.

Guide-only before/after from `tmp\guide_condition_probe_allguide_after1` to `tmp\guide_action_probe_allguide_after1`:

| Metric | Before | After |
| --- | ---: | ---: |
| Guide JSON files | 1,621 | 1,621 |
| Guide `$unparsed` managed refs | 5,864 | 3,951 |
| Decoded guide managed refs | 2,728 | 4,641 |

Resolved `$unparsed` payloads in this pass: 1,913.

Decoded action refs in the guide-only probe:

| Class | Decoded refs |
| --- | ---: |
| `GuideUnFreezeWorld` | 208 |
| `RecoverMainHud` | 200 |
| `GuideFreezeWorld` | 187 |
| `FinishEffect` | 152 |
| `FacLockBuildPos` | 142 |
| `SetFacTopView` | 138 |
| `ExitFacBuildMode` | 129 |
| `FacSetEnableConfirmBuild` | 111 |
| `SetEnablePlayerMove` | 107 |
| `SetFacMode` | 106 |
| `SetEnablePlayerMoveCamera` | 105 |
| `ToggleQuickMenuReleaseClose` | 79 |
| `FacSetEnableExitBuildMode` | 72 |
| `SetGeneralAbilityReleaseClose` | 45 |
| `ToggleGeneralAbilityLoneClick` | 42 |
| `ToggleGeneralAbilityClick` | 41 |
| `ToggleClearScreen` | 40 |
| `DisableHudFade` | 6 |
| `SetAtbValue` | 3 |

Largest remaining guide `$unparsed` classes after this pass:

| Class | Remaining refs | Current blocker |
| --- | ---: | --- |
| `BlendToCameraTransformWithoutBack` | 468 | Large 248-byte camera payload; IL2CPP names are known but exact vector/rotation/FOV tail grouping still needs validation. |
| `BlendOutFromCamera` | 319 | 104-byte camera payload with blend/style/black-screen/runtime fields; exact field order still needs validation. |
| `RemoveTrackingPoint` | 316 | Tracking-point list/key layout not yet mapped. |
| `FacHighlightBuilding` | 256 | String plus bool factory action is visible but variable string lengths need a guarded decoder pass. |
| `CheckScriptTaskStateEqual` | 249 | Condition wrapper and script-task state field names/order need proof. |
| `AddTrackingPoint` | 175 | Tracking-point list/key layout not yet mapped. |
| `FacGuideHintEnable` | 167 | String plus bool factory action is visible but variable string lengths need a guarded decoder pass. |
| `OnBuildingPanelOpen` | 127 | Condition payload not yet mapped. |
| `OnUIPanelClose` | 124 | Condition payload not yet mapped. |
| `PlayerHasItemInItemBag` | 94 | Item condition payload not yet mapped. |

Current classification: guide action decoding is improving the broad fresh-audit marker count without introducing AnimeStudio warnings. The remaining guide payloads are mostly larger camera/tracking/factory actions and additional item/quest/UI conditions, not signs of encryption or missing AB/VFS extraction.

Parallel component/projectile audit result reserved for the next batch: `ProjectileRootComponentData`, `WeaponData`, `StaticWeaponData`, `ObservedComponentData`, `CharacterAIComponentData`, and the 120-byte default `CharacterPivotComponentData` have stable minimal layouts. Larger `CharacterPivotComponentData` payloads need a real `AnimationCurve` decoder, and `ProjectileTemplateData` should be handled as a guarded partial parser because 77 long entries exceeded the current audit hint cap.

## 2026-06-29 Eleventh Fresh StreamingAssets Guide-Camera Action Batch

Follow-up after the tenth guide-action batch. Two read-only subagents independently validated the guide action base and camera/HUD layouts against the fresh audit and guide-only probes. No subagent edited files.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Refined guide action base semantics from an anonymous 36-byte prefix plus `trailingWord` into an action-chain record with `actionId`, 8-character action key, inherited raw words, `triggerActiveDuringRaw`, `validate`, and `nextId`.
- Replaced simple action tail readers with typed guide parameter wrappers:
  - `Param<T>` as `paramSource`, `path`, `value`, and `idRef`.
  - `ParamOutput<T>` as `paramTarget` and `path`.
- Re-decoded existing simple actions through those parameter wrappers, including the two path-backed `FacLockBuildPos` variants that the previous bool-only interpretation left unparsed.
- Added camera action decoders proven by strict all-sample validation:
  - `BlendToCameraTransformWithoutBack`
  - `BlendOutFromCamera`
  - `BlendIntoCameraNoReturn`
- Kept runtime/nonserialized fields out of the JSON: camera `m_stage` fields, `m_handleId`, `m_targetPos`, `m_targetRot`, `m_targetFov`, and guide freeze runtime handles remain intentionally absent rather than guessed.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\guide_camera_probe_allguide_after1 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^guide_"
```

Build result: success with existing project compile warnings and `0` errors. The guide-only probe emitted 1,621 MonoBehaviour JSON files with exit code 0. Log grep for `Warning`, `Error`, `metadata-only JSON`, partial-TypeTree warnings, `Export ... error`, and `Unknown ClassIDType` returned no matches.

Guide-only before/after from `tmp\guide_action_probe_allguide_after1` to `tmp\guide_camera_probe_allguide_after1`:

| Metric | Before | After |
| --- | ---: | ---: |
| Guide JSON files | 1,621 | 1,621 |
| Guide `$unparsed` managed refs | 3,951 | 3,148 |
| Decoded guide managed refs | 4,641 | 5,444 |

Resolved `$unparsed` payloads in this pass: 803.

Resolved classes:

| Class | Resolved refs |
| --- | ---: |
| `BlendToCameraTransformWithoutBack` | 468 |
| `BlendOutFromCamera` | 319 |
| `BlendIntoCameraNoReturn` | 14 |
| `FacLockBuildPos` path-backed variants | 2 |

Largest remaining guide `$unparsed` classes after this pass:

| Class | Remaining refs | Current blocker |
| --- | ---: | --- |
| `RemoveTrackingPoint` | 316 | Tracking-point list/key layout not yet mapped. |
| `FacHighlightBuilding` | 256 | Factory string+bool parameter layout needs strict validation. |
| `CheckScriptTaskStateEqual` | 249 | Script-task condition wrapper and state fields need exact mapping. |
| `AddTrackingPoint` | 175 | Tracking-point list/key layout not yet mapped. |
| `FacGuideHintEnable` | 167 | Factory string+bool parameter layout needs strict validation. |
| `OnBuildingPanelOpen` | 127 | Condition payload not yet mapped. |
| `OnUIPanelClose` | 124 | Condition payload not yet mapped. |
| `PlayerHasItemInItemBag` | 94 | Item condition payload not yet mapped. |
| `CreateEffectAtPosition` | 89 | Effect action parameters need exact mapping. |
| `CheckQuestState` | 78 | Quest condition payload not yet mapped. |

Current classification: the largest camera-action guide bucket is now understood and structurally decoded. The remaining guide bucket is no longer dominated by camera data; it is concentrated in tracking-point actions, factory string/bool actions, and item/quest/UI conditions. This continues to look like managed-reference schema recovery work, not encryption or missing VFS extraction.

## 2026-06-29 Twelfth Fresh StreamingAssets Guide-Action-Condition Batch

Follow-up after the eleventh guide-camera action batch. Two read-only subagents mapped the next high-count guide action and condition buckets from `tmp\guide_action_probe_allguide_after1` and the fresh StreamingAssets audit, using IL2CPP metadata names where available. No subagent edited files.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added guide action decoders for:
  - `RemoveTrackingPoint`
  - `FacHighlightBuilding`
  - `AddTrackingPoint`
  - `FacGuideHintEnable`
  - `CreateEffectAtPosition`
  - `FacSetInteractLockedState`
  - `ToggleScrollRect`
  - `FacConveyorInteractRangeRestrict`
  - `ScrollToItemBagTargetItem`
  - `FocusOnInteractOption`
- Added guide condition decoders for:
  - `CheckScriptTaskStateEqual`
  - `OnBuildingPanelOpen`
  - `OnUIPanelClose`
  - `PlayerHasItemInItemBag`
  - `CheckQuestState`
  - `PlayerHasItem`
  - `CheckIsInFactoryMode`
  - `OnFacPrepareBuildingEnterArea`
  - `OnFacPlaceBuilding`
  - `DepotHasItem`
  - `CheckActivityStageInTimeOffset`
  - `CheckIsInGeneralAbilitySelectMode`
  - `CheckCurrentMap`
- Added guide parameter helpers for string, int64, float, vector3, and the `CheckScriptTaskStateEqual` task-key wrapper with its extra raw word.
- Kept enum-like fields numeric where value-to-name mappings are not proven, including tracking style/type and guide condition comparers/operators.
- Left runtime/cache-only IL2CPP fields unread when no serialized payload bytes exist, such as `CreateEffectAtPosition.m_instanceIdList` and several condition cache fields.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\guide_actions_conditions_probe_allguide_after2 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^guide_"
```

Final build result: success with `0` warnings and `0` errors. The guide-only probe emitted 1,621 MonoBehaviour JSON files with exit code 0. Log grep for `Warning`, `Error`, `metadata-only JSON`, partial-TypeTree warnings, `Export ... error`, and `Unknown ClassIDType` returned no matches.

Guide-only before/after from `tmp\guide_camera_probe_allguide_after1` to `tmp\guide_actions_conditions_probe_allguide_after2`:

| Metric | Before | After |
| --- | ---: | ---: |
| Guide JSON files | 1,621 | 1,621 |
| Guide `$unparsed` managed refs | 3,148 | 928 |
| Decoded guide managed refs | 5,444 | 7,664 |

Resolved `$unparsed` payloads in this pass: 2,220.

Resolved classes:

| Class | Resolved refs |
| --- | ---: |
| `RemoveTrackingPoint` | 316 |
| `FacHighlightBuilding` | 256 |
| `CheckScriptTaskStateEqual` | 249 |
| `AddTrackingPoint` | 175 |
| `FacGuideHintEnable` | 167 |
| `OnBuildingPanelOpen` | 127 |
| `OnUIPanelClose` | 124 |
| `PlayerHasItemInItemBag` | 94 |
| `CreateEffectAtPosition` | 89 |
| `CheckQuestState` | 78 |
| `PlayerHasItem` | 77 |
| `CheckIsInFactoryMode` | 71 |
| `FacSetInteractLockedState` | 48 |
| `ToggleScrollRect` | 42 |
| `OnFacPrepareBuildingEnterArea` | 42 |
| `OnFacPlaceBuilding` | 39 |
| `FacConveyorInteractRangeRestrict` | 36 |
| `DepotHasItem` | 34 |
| `CheckActivityStageInTimeOffset` | 32 |
| `ScrollToItemBagTargetItem` | 32 |
| `CheckIsInGeneralAbilitySelectMode` | 32 |
| `FocusOnInteractOption` | 30 |
| `CheckCurrentMap` | 30 |

Largest remaining guide `$unparsed` classes after this pass:

| Class | Remaining refs | Current blocker |
| --- | ---: | --- |
| `OnInteractOptionShow` | 28 | Condition payload not yet mapped. |
| `ToggleGeneralAbilityHide` | 28 | Action payload not yet mapped. |
| `SelectQuickMenuSystem` | 27 | Action payload not yet mapped. |
| `OnQuickMenuSystemHover` | 27 | Condition payload not yet mapped. |
| `BuildingPosHintHide` | 27 | Action payload not yet mapped. |
| `FacBlockOtherHubUnloaderInteract` | 27 | Action payload not yet mapped. |
| `ToggleAbandonDropValid` | 27 | Action payload not yet mapped. |
| `FocusTechTreeNode` | 26 | Action payload not yet mapped. |
| `CheckIsInFacMainRegion` | 25 | Condition payload not yet mapped. |
| `CheckHasInteractOption` | 24 | Condition payload not yet mapped. |
| `CheckCurrentLevel` | 22 | Condition payload not yet mapped. |
| `OnOpenFacUnloaderPanel` | 21 | Condition payload not yet mapped. |
| `CorrectPlayerPosTeleport` | 21 | Action payload not yet mapped. |

Current classification: the guide/tutorial managed-reference bucket has moved from broad high-count unknown action/condition layouts to a long tail of smaller action/condition classes. The remaining markers still look like serialized managed-reference schema recovery work, not encryption or missing VFS extraction.

## 2026-06-29 Thirteenth Fresh StreamingAssets Guide-Tail Batch

Follow-up after the twelfth guide action/condition batch. Two read-only subagents independently validated the next high-count guide action and condition buckets from `tmp\guide_actions_conditions_probe_allguide_after2` using strict payload consumption and IL2CPP field names where available. No subagent edited files.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added guide action decoders for:
  - `ToggleGeneralAbilityHide`
  - `SelectQuickMenuSystem`
  - `BuildingPosHintHide`
  - `FacBlockOtherHubUnloaderInteract`
  - `ToggleAbandonDropValid`
  - `FocusTechTreeNode`
  - `CorrectPlayerPosTeleport`
  - `BuildingPosHintShow`
  - `ScrollToBuildListTargetItem`
  - `ForceEnableControllerNavi`
  - `SetMainHudCanAutoStopExpand`
- Added guide condition decoders for:
  - `OnInteractOptionShow`
  - `OnQuickMenuSystemHover`
  - `CheckIsInFacMainRegion`
  - `CheckHasInteractOption`
  - `CheckCurrentLevel`
  - `OnOpenFacUnloaderPanel`
  - `OnFacCurMachineCacheAddItem`
  - `OnFacQuickBarAddItem`
  - `OnUIScrollListGraduallyShowFinished`
  - `CheckIsInFacLinkingMode`
  - `OnGeneralAbilityHover`
  - `CheckActivityCompletedOrNull`
  - `CheckUnlockTech`
  - `CheckPlayerInMap`
  - `CheckBuildingStateInArea`
- Kept enum-like fields numeric where value-to-name mappings are not proven, including `closeSelectAbilityType`, `worldDir`, `abilityType`, `facStateType`, and `targetFacLinkingModeType`.
- Left runtime/static IL2CPP fields unread when no serialized payload bytes exist, including `BuildingPosHintShow.m_handle`, `CheckHasInteractOption.s_activeConditions`, `OnUIScrollListGraduallyShowFinished.s_inited`, and `CheckUnlockTech.m_facTechId`.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\guide_tail_probe_allguide_after4 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^guide_"
```

Final build result: success with `0` warnings and `0` errors. The guide-only probe emitted 1,621 MonoBehaviour JSON files with exit code 0. Log grep for `Warning`, `Error`, `metadata-only JSON`, partial-TypeTree warnings, `Export ... error`, and `Unknown ClassID` returned no matches.

Guide-only before/after from `tmp\guide_actions_conditions_probe_allguide_after2` to `tmp\guide_tail_probe_allguide_after4`:

| Metric | Before | After |
| --- | ---: | ---: |
| Guide JSON files | 1,621 | 1,621 |
| Guide `$unparsed` managed refs | 928 | 386 |
| Decoded guide managed refs | 7,664 | 8,206 |

Resolved `$unparsed` payloads in this pass: 542.

Resolved classes:

| Class | Resolved refs |
| --- | ---: |
| `ToggleGeneralAbilityHide` | 28 |
| `OnInteractOptionShow` | 28 |
| `SelectQuickMenuSystem` | 27 |
| `OnQuickMenuSystemHover` | 27 |
| `BuildingPosHintHide` | 27 |
| `FacBlockOtherHubUnloaderInteract` | 27 |
| `ToggleAbandonDropValid` | 27 |
| `FocusTechTreeNode` | 26 |
| `CheckIsInFacMainRegion` | 25 |
| `CheckHasInteractOption` | 24 |
| `CheckCurrentLevel` | 22 |
| `OnOpenFacUnloaderPanel` | 21 |
| `CorrectPlayerPosTeleport` | 21 |
| `OnFacCurMachineCacheAddItem` | 20 |
| `BuildingPosHintShow` | 20 |
| `CheckActivityCompletedOrNull` | 20 |
| `OnFacQuickBarAddItem` | 19 |
| `OnUIScrollListGraduallyShowFinished` | 18 |
| `CheckIsInFacLinkingMode` | 17 |
| `ScrollToBuildListTargetItem` | 17 |
| `OnGeneralAbilityHover` | 16 |
| `CheckUnlockTech` | 16 |
| `CheckBuildingStateInArea` | 15 |
| `ForceEnableControllerNavi` | 14 |
| `CheckPlayerInMap` | 10 |
| `SetMainHudCanAutoStopExpand` | 10 |

Largest remaining guide `$unparsed` classes after this pass:

| Class | Remaining refs | Current blocker |
| --- | ---: | --- |
| `OnDungeonCommonEntryPanelOpen` | 13 | Condition payload not yet mapped. |
| `OnFacConveyorOperated` | 12 | Condition payload not yet mapped. |
| `EquipProduceScrollToItem` | 12 | Action payload not yet mapped. |
| `BlendToCameraTransform` | 11 | Action payload not yet mapped. |
| `FacToggleCanDeactiveQuickBar` | 11 | Action payload not yet mapped. |
| `CheckAdventureLevel` | 10 | Condition payload has comparer/progress fields; exact leading field still needs validation. |
| `FacOverrideCullingSetting` | 9 | Action payload not yet mapped. |
| `ClickUI` | 9 | Action payload not yet mapped. |
| `EnterFacBeltBuildMode` | 9 | Action payload likely fieldless or static-only, but needs strict validation. |
| `OnCharInfoModelInitFinish` | 9 | Condition payload not yet mapped. |
| `CheckIsSquadInFight` | 9 | Condition payload not yet mapped. |
| `CheckPlayerOnGround` | 9 | Condition payload not yet mapped. |
| `SelectMapMark` | 9 | Action payload not yet mapped. |

Current classification: the guide/tutorial managed-reference bucket is now a small long tail. The fresh probe has no exporter warnings/errors, and the remaining guide `$unparsed` entries still look like ordinary managed-reference layout recovery, not encryption, missing VFS extraction, or multi-layer AB encryption.

## 2026-06-29 Fourteenth Fresh StreamingAssets Guide-Tail Batch

Follow-up after the thirteenth guide-tail batch. Two read-only subagents validated the next guide action and condition long-tail buckets from `tmp\guide_tail_probe_allguide_after4` with strict payload replay and IL2CPP field names where available. No subagent edited files.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added guide action decoders/classifiers for `EquipProduceScrollToItem`, `BlendToCameraTransform`, `FacToggleCanDeactiveQuickBar`, `FacOverrideCullingSetting`, `ClickUI`, `EnterFacBeltBuildMode`, `SelectMapMark`, `FacMainHudCloseMobileBox`, `HideItemTips`, `ToggleSideMenuItemForceValid`, `FacMainHudRightStopFocus`, `SelectAdventureBookTab`, `UIScrollRectScrollTo`, `FacOpenBuildingPanel`, `FacHighlightBuildingInArea`, `Split`, `BlackScreenFadeOut`, `ToggleItemTipsAutoClose`, `FacSetEnableExitFactoryMode`, `ClearFacPin`, `ZoomToFullTechTree`, `CharInfoSwitchChar`, `CharInfoWeaponScrollToTop`, and `ExitCharInfoTalentExpandNode`.
- Added guide condition decoders/classifiers for `OnDungeonCommonEntryPanelOpen`, `OnFacConveyorOperated`, `CheckAdventureLevel`, `OnCharInfoModelInitFinish`, `CheckIsSquadInFight`, `CheckPlayerOnGround`, `CheckIsInFacTopView`, `CheckSelectGeneralAbility`, `CheckIsItemInQuickBar`, `CheckInWeaponUpgradePanel`, `OnSTTAllOpenProgressFinished`, `CheckBuildingConnectedSpecify`, `CheckIsOpenDomainMain`, `CheckMapMissionTrackingState`, `OnUILevelMapEnterLevel`, `OnCastComboSkill`, `CheckBlackboxComplete`, `OnOpenFacHubPanelWithoutNotify`, `OnOtherPlayerSocialBuildingPanelOpen`, `CheckIsPhaseCharInfoDefaultChar`, `OnMainHudActionFinished`, `CheckSimulationTrainingHandCardCount`, `CheckSpaceshipRoomLevel`, `CheckInCharInfoUpgradePanel`, `OnNormalFriendPanelOpen`, `OnEnterMainHud`, `OnFacReachFastTravel`, `OnComboSkillReady`, `OnMixPoolSelectFinish`, `OnGeneralAbilityUse`, `OnLiquidInteractInDumpMode`, and `OnFacPendingSlotChanged`.
- Added small helpers for the guide two-int condition wrapper and raw int32 guide lists. `Split._idList` is preserved as raw/hash-like int32 values because only list structure is proven.
- Kept enum-like and id-like fields numeric/raw where labels are not proven, including `blendStyle`, `_type`, `comparer`, `progressToCompare`, `conveyorType`, `completeState`, `roomType`, and guide wrapper ids.
- Left runtime/static IL2CPP fields unread when no serialized payload bytes exist, such as `BlendToCameraTransform.m_stage/m_usedBlackScreen/m_handleId`, `CheckAdventureLevel.BLOCK_DESC_FORMATTER`, and spaceship/runtime cache fields.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\guide_tail_probe_allguide_after5 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^guide_"
```

Build result: success with `0` errors. The first non-incremental build after editing emitted the existing AnimeStudio project warnings, not new compile errors. The guide-only probe emitted 1,621 MonoBehaviour JSON files with exit code 0. Log grep for `Warning`, `Error`, `metadata-only JSON`, partial-TypeTree warnings, `Export ... error`, and `Unknown ClassID` returned no matches.

Guide-only before/after from `tmp\guide_tail_probe_allguide_after4` to `tmp\guide_tail_probe_allguide_after5`:

| Metric | Before | After |
| --- | ---: | ---: |
| Guide JSON files | 1,621 | 1,621 |
| Guide `$unparsed` managed refs | 386 | 62 |
| Decoded guide managed refs | 8,206 | 8,530 |

Resolved `$unparsed` payloads in this pass: 324.

Largest resolved classes:

| Class | Resolved refs |
| --- | ---: |
| `OnDungeonCommonEntryPanelOpen` | 13 |
| `OnFacConveyorOperated` | 12 |
| `EquipProduceScrollToItem` | 12 |
| `BlendToCameraTransform` | 11 |
| `FacToggleCanDeactiveQuickBar` | 11 |
| `CheckAdventureLevel` | 10 |
| `OnCharInfoModelInitFinish` | 9 |
| `CheckPlayerOnGround` | 9 |
| `CheckIsSquadInFight` | 9 |
| `SelectMapMark` | 9 |
| `FacOverrideCullingSetting` | 9 |
| `EnterFacBeltBuildMode` | 9 |
| `ClickUI` | 9 |
| `HideItemTips` | 8 |
| `FacMainHudCloseMobileBox` | 8 |
| `UIScrollRectScrollTo` | 7 |
| `ToggleSideMenuItemForceValid` | 7 |
| `SelectAdventureBookTab` | 7 |
| `FacMainHudRightStopFocus` | 7 |

Remaining guide `$unparsed` classes after this pass:

| Class | Remaining refs |
| --- | ---: |
| `CheckRepairBuilding` | 3 |
| `FacBuildingProducingCountInScene` | 3 |
| `OnGetItem` | 3 |
| `HasItemCount` | 3 |
| `OnTechTreeNodeUnlock` | 3 |
| `CheckWorldLevel` | 3 |
| `CheckItemBagCanPutInServer` | 3 |
| `CheckWireLinkAvailable` | 3 |
| `CheckPlayerPin` | 3 |
| `CheckCharInMainTeam` | 3 |
| `CheckIsWeaponEquipped` | 3 |
| `FocusTechTreeLayer` | 3 |
| `FocusTechTreeCategory` | 3 |
| `NaviToMixPoolTargetItem` | 2 |
| `SetEnablePlayerAction` | 2 |
| `ShowLimitedGuide` | 2 |
| `CheckUnlockTechLayer` | 2 |
| `UIScrollListScrollTo` | 2 |
| `CheckSpaceshipRoomStationCount` | 2 |
| `CheckDomainShopChannelLevel` | 2 |
| Nine additional classes | 1 each |

Current classification: the guide/tutorial managed-reference bucket is now reduced to 62 refs spread across tiny classes. The fresh probe still has no export warnings/errors, and the remaining entries continue to look like ordinary managed-reference layout recovery rather than encryption, missing VFS extraction, or multi-layer AB encryption.

## 2026-06-29 Fifteenth Fresh StreamingAssets Guide-Tail Batch

Follow-up after the fourteenth guide-tail batch. A read-only action subagent validated the last remaining guide action layouts from `tmp\guide_tail_probe_allguide_after5` with strict payload replay and IL2CPP field names. The condition/root-condition layouts were validated locally with the same strict replay method plus IL2CPP metadata names. A second condition subagent was closed before returning a final table, so it is not used as evidence for this batch.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added guide action decoders/classifiers for:
  - `FocusTechTreeLayer`
  - `FocusTechTreeCategory`
  - `NaviToMixPoolTargetItem`
  - `SetEnablePlayerAction`
  - `ShowLimitedGuide`
  - `UIScrollListScrollTo`
- Added guide condition/root-condition decoders/classifiers for:
  - `CheckRepairBuilding`
  - `FacBuildingProducingCountInScene`
  - `OnGetItem`
  - `HasItemCount`
  - `OnTechTreeNodeUnlock`
  - `CheckWorldLevel`
  - `CheckItemBagCanPutInServer`
  - `CheckWireLinkAvailable`
  - `CheckPlayerPin`
  - `CheckCharInMainTeam`
  - `CheckIsWeaponEquipped`
  - `CheckUnlockTechLayer`
  - `CheckSpaceshipRoomStationCount`
  - `CheckDomainShopChannelLevel`
  - `FacStatisticItemGenRate`
  - `FacStatisticItemGen`
  - `FacProducePowerReach`
  - `FacProducingFormulaCountInScene`
  - `CheckDomainShopPanelHasSoldOutGroup`
  - `OnFacMainPinHintShow`
  - `CheckGachaWeaponTopCount`
  - `OnWeekRaidIntroCharFormationOpen`
  - `CheckSpaceshipRoomBuiltById`
- Kept wrapper/base ids, action masks, comparer/operator fields, room/tech/factory enum-like fields, and raw statistic wrappers numeric/raw where value-to-name mappings are not proven.
- Left runtime/static IL2CPP fields unread when no serialized bytes exist, including action handles, cached formula/room fields, and static constants.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" tmp\guide_tail_probe_allguide_after6 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^guide_"
```

Build result: success with `0` errors. The build emitted the existing AnimeStudio project warnings, not new compile errors. The guide-only probe emitted 1,621 MonoBehaviour JSON files with exit code 0. Log grep for `Warning`, `Error`, `metadata-only JSON`, partial-TypeTree warnings, `Export ... error`, and `Unknown ClassID` returned no matches.

Guide-only before/after from `tmp\guide_tail_probe_allguide_after5` to `tmp\guide_tail_probe_allguide_after6`:

| Metric | Before | After |
| --- | ---: | ---: |
| Guide JSON files | 1,621 | 1,621 |
| Guide `$unparsed` managed refs | 62 | 0 |
| Decoded guide managed refs | 8,530 | 8,592 |

Resolved `$unparsed` payloads in this pass: 62.

Resolved classes:

| Class | Resolved refs |
| --- | ---: |
| `HasItemCount` | 3 |
| `FacBuildingProducingCountInScene` | 3 |
| `OnTechTreeNodeUnlock` | 3 |
| `OnGetItem` | 3 |
| `CheckWireLinkAvailable` | 3 |
| `CheckIsWeaponEquipped` | 3 |
| `CheckWorldLevel` | 3 |
| `CheckRepairBuilding` | 3 |
| `CheckPlayerPin` | 3 |
| `CheckItemBagCanPutInServer` | 3 |
| `CheckCharInMainTeam` | 3 |
| `FocusTechTreeLayer` | 3 |
| `FocusTechTreeCategory` | 3 |
| `CheckUnlockTechLayer` | 2 |
| `CheckSpaceshipRoomStationCount` | 2 |
| `CheckDomainShopChannelLevel` | 2 |
| `UIScrollListScrollTo` | 2 |
| `ShowLimitedGuide` | 2 |
| `SetEnablePlayerAction` | 2 |
| `NaviToMixPoolTargetItem` | 2 |
| `FacStatisticItemGenRate` | 1 |
| `FacStatisticItemGen` | 1 |
| `FacProducingFormulaCountInScene` | 1 |
| `FacProducePowerReach` | 1 |
| `OnWeekRaidIntroCharFormationOpen` | 1 |
| `OnFacMainPinHintShow` | 1 |
| `CheckDomainShopPanelHasSoldOutGroup` | 1 |
| `CheckSpaceshipRoomBuiltById` | 1 |
| `CheckGachaWeaponTopCount` | 1 |

Current classification: the targeted guide/tutorial managed-reference bucket is structurally decoded in fresh installed `StreamingAssets`: zero guide `$unparsed` managed refs, no guide probe warning/error log matches, and no indication that the remaining guide issues were encryption or missing VFS extraction. This does not prove every non-guide exported file type is fully understood; it closes the guide managed-reference bucket for the current installed data.

## 2026-06-29 Sixteenth Fresh StreamingAssets Empty-Payload Component Batch

Follow-up after the guide-tail cleanup. Two read-only subagents split the next unresolved non-guide MonoBehaviour surface:

- Inventory subagent: parsed the broad fresh audit marker lists and confirmed the largest non-guide buckets are managed-reference schema/layout gaps, not missing VFS chunks or repeated encryption.
- Decoder-candidate subagent: identified projectile/component classes and the safer exact zero-payload component group. It also noted that projectile/component full decoding should not be claimed until nested collider/effect/audio/list sections are proven.

A complete non-guide marker scan over `tmp\fresh_json_audit_20260629_streaming\MonoBehaviour` was run with guide files excluded because `tmp\guide_tail_probe_allguide_after6` proves guide refs are now zero:

```bat
rg -l --fixed-strings "$unparsed" --glob "!guide_*.json" tmp\fresh_json_audit_20260629_streaming\MonoBehaviour > tmp\fresh_audit_unparsed_nonguide_files.txt
rg -l --fixed-strings "decodeError" --glob "!guide_*.json" tmp\fresh_json_audit_20260629_streaming\MonoBehaviour > tmp\fresh_audit_decodeerror_nonguide_files.txt
```

Current non-guide marker inventory from those complete scans:

| Metric | Count |
| --- | ---: |
| Non-guide `$unparsed` files | 609 |
| Non-guide `decodeError` files | 788 |
| Union marker files parsed | 788 |
| `ReadAlignedString` decode-error shapes | 733 |
| Negative string-length decode-error shapes | 51 |
| No-bytes decode-error shapes | 4 |

Largest remaining non-guide `$unparsed` classes before this batch:

| Class | Refs | Files |
| --- | ---: | ---: |
| `Beyond.Gameplay.ProjectileTemplateData` | 300 | 300 |
| `Beyond.Gameplay.Core.ProjectileRootComponentData` | 300 | 300 |
| `Beyond.Gameplay.Core.ProjectileComponentData` | 300 | 300 |
| `Beyond.Gameplay.PlaySingleSound` | 189 | 95 |
| `Beyond.Gameplay.PlaySoundByParticleCount` | 169 | 85 |
| `Beyond.Gameplay.WikiModelSpawnData` | 129 | 1 |
| `Beyond.Gameplay.WeaponDecoEffectData` | 73 | 1 |
| `Beyond.Gameplay.WeaponData` | 45 | 28 |
| `Beyond.Gameplay.StaticWeaponData` | 41 | 15 |
| `Beyond.Gameplay.View.Animation.CharacterPivotComponentData` | 39 | 30 |

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added explicit decoded empty managed-reference records for observed zero-length payload classes where the serialized type identity is the entire payload:
  - `Beyond.Gameplay.View.LookAtComponentData`
  - `Beyond.Gameplay.Core.CharacterControllerData`
  - `Beyond.Gameplay.Core.CharacterAudioComponentData`
  - `Beyond.Gameplay.Core.CharacterBlowOffComponentData`
  - `Beyond.Gameplay.Core.StateTransitionComponentData`
  - `Beyond.Gameplay.Core.RemoteFactoryMineComponentData`
  - `Beyond.Gameplay.Core.Selector/CharacterTeamFinder/Data`
  - `Beyond.Gameplay.Core.Selector/MainCharacterValidator/Data`
  - `Beyond.Gameplay.DynamicBattleShapeComponentData`
  - `Beyond.Gameplay.CustomAbilityComponentData`
  - `Beyond.Gameplay.InteractiveEvent.InteractiveInstigatorControlComponentData`
  - `Beyond.Gameplay.InteractiveEvent.DetachFromInstigator`
  - `Beyond.Gameplay.InteractiveEvent.ClearInstigator`
  - `Beyond.Gameplay.InteractiveEvent.SetInstigator`
  - `Beyond.Gameplay.InteractiveEvent.AddThrowCameraControl`
  - `Beyond.Gameplay.InteractiveEvent.ThrowByForceAndDir`
  - `Beyond.Gameplay.InteractiveEvent.TriggerPickUpAction`
- The decoders are guarded by `length == 0`; non-empty payloads still fall through to the existing marker path.
- The emitted JSON includes `layoutNote` explaining that zero serialized payload length makes type identity the complete exported data for that managed-reference entry.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\empty_payload_all_validation_after\chunk1 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\empty_payload_all_validation_filters\names_1.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\empty_payload_all_validation_after\chunk2 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\empty_payload_all_validation_filters\names_2.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\empty_payload_all_validation_after\chunk3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\empty_payload_all_validation_filters\names_3.txt
```

Build result: success with `0` errors and the existing 14 project warnings. The three targeted exports covered 38 JSON files across 3 source chunks, exited with code 0, and emitted no warning/error output.

Targeted before/after across those 38 files:

| Metric | Before | After |
| --- | ---: | ---: |
| `$unparsed` refs | 860 | 588 |
| decoded refs | 312 | 584 |
| partial refs | 45 | 45 |
| `decodeError` refs | 0 | 0 |

Resolved `$unparsed` refs in this batch: 272.

Resolved classes:

| Class | Resolved refs |
| --- | ---: |
| `Beyond.Gameplay.View.LookAtComponentData` | 29 |
| `Beyond.Gameplay.Core.CharacterControllerData` | 28 |
| `Beyond.Gameplay.InteractiveEvent.InteractiveInstigatorControlComponentData` | 28 |
| `Beyond.Gameplay.Core.CharacterAudioComponentData` | 28 |
| `Beyond.Gameplay.Core.CharacterBlowOffComponentData` | 28 |
| `Beyond.Gameplay.Core.StateTransitionComponentData` | 28 |
| `Beyond.Gameplay.DynamicBattleShapeComponentData` | 28 |
| `Beyond.Gameplay.CustomAbilityComponentData` | 28 |
| `Beyond.Gameplay.InteractiveEvent.DetachFromInstigator` | 11 |
| `Beyond.Gameplay.InteractiveEvent.ClearInstigator` | 11 |
| `Beyond.Gameplay.InteractiveEvent.SetInstigator` | 6 |
| `Beyond.Gameplay.InteractiveEvent.AddThrowCameraControl` | 5 |
| `Beyond.Gameplay.InteractiveEvent.ThrowByForceAndDir` | 5 |
| `Beyond.Gameplay.Core.RemoteFactoryMineComponentData` | 3 |
| `Beyond.Gameplay.InteractiveEvent.TriggerPickUpAction` | 2 |
| `Beyond.Gameplay.Core.Selector/CharacterTeamFinder/Data` | 2 |
| `Beyond.Gameplay.Core.Selector/MainCharacterValidator/Data` | 2 |

Top remaining unresolved classes in the validated files after this batch are `WeaponData`, `StaticWeaponData`, `WeaponDataWrapper`, character template/root/view/AI component data, `ObservedComponentData`, `CharHurtAnimComponentData`, `CharacterPivotComponentData`, and `WaterSensorComponentData`. Full non-guide next buckets remain projectile managed references, sound action payloads, and character/weapon component schemas. Current classification: this batch reduces false unresolved markers for zero-byte managed-reference entries only; the remaining non-guide work is schema/layout recovery, not missing AB/VFS extraction or multi-layer encryption.

## 2026-06-29 Seventeenth Fresh StreamingAssets Projectile-Root Batch

Follow-up after the empty-payload component batch. Work focused on the largest remaining non-guide projectile managed-reference family from `tmp\fresh_audit_unparsed_nonguide_files.txt`.

A read-only subagent independently audited `Beyond.Gameplay.Core.ProjectileRootComponentData` and confirmed:

- Marker list checked: 609 non-guide `$unparsed` files, 0 JSON parse errors.
- Unresolved `ProjectileRootComponentData` occurrences: 300 in 300 files, exactly one per file.
- Every target payload has `dataLength == 32`.
- The raw int32 vector has one unique value across all 300 entries: eight zero words.
- Installed IL2CPP metadata has one matching type `Beyond.Gameplay.Core.ProjectileRootComponentData` in `Gameplay.Beyond.dll`, metadata version 29, `field_count = 0`, no own fields, and only a parameterless `.ctor` method.

Local verification produced the same byte-shape result:

```text
count 300, files 300, lengths {32: 300}, exceptions 0
```

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added a guarded decoder for `Gameplay.Beyond / Beyond.Gameplay.Core / ProjectileRootComponentData`.
- The decoder requires `length == 32` and consumes exactly eight int32 words.
- Every word must be zero; any nonzero word throws and falls back to the existing marker path.
- Output is marked decoded with `reservedZeroWords` and a `layoutNote` explaining that current installed data serializes the fieldless component as a 32-byte reserved-zero payload.
- This is not a generic empty-class rule and does not affect `ProjectileTemplateData` or `ProjectileComponentData`.

Validation:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\projectile_root_validation_after\chunk1 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\projectile_root_validation_filters\names_1.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\projectile_root_validation_after\chunk2 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\projectile_root_validation_filters\names_2.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\projectile_root_validation_after\chunk3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\projectile_root_validation_filters\names_3.txt
```

Build result: success with `0` errors and the existing 14 project warnings. The three targeted exports covered all 300 projectile files across three source chunks, exited with code 0, and emitted no warning/error output.

Projectile family before/after in the targeted validation set:

| Class | Before `$unparsed` | After `$unparsed` | After decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.ProjectileTemplateData` | 300 | 300 | 0 |
| `Beyond.Gameplay.Core.ProjectileRootComponentData` | 300 | 0 | 300 |
| `Beyond.Gameplay.Core.ProjectileComponentData` | 300 | 300 | 0 |

Resolved `$unparsed` refs in this batch: 300. No invalid reserved-zero payloads were found. Current classification: `ProjectileRootComponentData` is now understood as a fieldless component with a reserved-zero serialized payload in current installed data. Remaining projectile work is still substantial: `ProjectileTemplateData` and `ProjectileComponentData` remain marked because their non-empty nested strings, RID links, collider/effect/audio/list sections, and movement data need full schema proof before decoding.

## 2026-06-29 Eighteenth Fresh StreamingAssets Sound-Action Batch

Follow-up after the projectile-root managed-reference batch. Work focused on the unresolved non-guide sound action payloads in `tmp\fresh_audit_unparsed_nonguide_files.txt`.

Read-only subagent evidence and local checks agreed on the current installed data shape:

- `Beyond.Gameplay.PlaySingleSound`: 189 unresolved refs in 95 files, every payload `dataLength == 28`.
- `Beyond.Gameplay.PlaySoundByParticleCount`: 169 unresolved refs in 85 files, payload lengths `60 x 168` and `44 x 1`.
- All 179 containing JSON files come from `StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk`.
- `PlaySingleSoundBase` has no direct unresolved payloads in this audit, but IL2CPP metadata exposes the serialized base fields used by `PlaySingleSound`: `soundSpawn`, `soundFinish`, `shouldTick`; `m_audioObj` is runtime-only in observed payloads.
- Installed metadata for `PlaySingleSound` exposes direct fields `isOverrideTrackingObj` and `overridedTrackingObj`.
- Installed metadata for `PlaySoundByParticleCount` exposes `soundName`, `particle`, `threshold`, and runtime-only `m_lastCount`.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Extended the general `Gameplay.Beyond` managed-reference decoder so non-empty, known sound payloads can decode before the existing zero-length known-empty fallback.
- Added strict `PlaySingleSound` decoding:
  - requires namespace `Beyond.Gameplay`, class `PlaySingleSound`, and `length == 28`
  - reads `soundBase.soundSpawn`, `soundBase.soundFinish`, `soundBase.shouldTick`, `isOverrideTrackingObj`, and `overridedTrackingObj` PPtr
  - bool fields use `ReadBool32`; the PPtr uses the existing `ReadPayloadPPtr`; any mismatch falls back to the existing marker path
- Added strict `PlaySoundByParticleCount` decoding:
  - requires namespace `Beyond.Gameplay`, class `PlaySoundByParticleCount`, and at least 20 bytes
  - reads aligned ASCII `soundName`
  - requires exactly 16 bytes after the string
  - reads `particle` PPtr plus `threshold` int32
  - any invalid string, remaining-length mismatch, or bad range falls back to the existing marker path

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\sound_action_validation_after\chunk1_offsets --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\sound_action_validation_filters\never_match.txt --filter_data tmp\sound_action_validation_filters\filter_data_1_offsets.json
```

The exact filter exported 179 JSON files. The filter had to use `filter_data` with internal `.chk` offsets recovered from `export_full\recovered\AnimeStudio-cli\StreamingAssets\maps\endfield_streamingassets_assets.json`; name filtering alone cannot target these objects because the exported `MonoBehaviour#...` names are generated fallbacks while the asset map name is just `MonoBehaviour`.

Build result: success. The final targeted export exited with code 0 and emitted no warning/error output.

Before/after across the 179 targeted files:

| Metric | Before | After |
| --- | ---: | ---: |
| `$unparsed` refs | 358 | 0 |
| decoded refs | 0 | 358 |
| partial refs | 0 | 0 |

Resolved classes:

| Class | Before `$unparsed` | After `$unparsed` | After decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.PlaySingleSound` | 189 | 0 | 189 |
| `Beyond.Gameplay.PlaySoundByParticleCount` | 169 | 0 | 169 |

Resolved `$unparsed` refs in this batch: 358. Current classification: these were plain serialized managed-reference payloads, not missing AB/VFS bytes and not encryption. Remaining high-value next buckets are `Beyond.Gameplay.ProjectileTemplateData` (300 refs, small and metadata-backed), `Beyond.Gameplay.WikiModelSpawnData` (129 refs, TypeTree-backed), and `Beyond.Gameplay.WeaponDecoEffectData` (73 refs, structurally plausible but field names should stay conservative). `ProjectileComponentData` remains much larger and should not be claimed exact before a staged component-layout probe.

## 2026-06-29 Nineteenth Fresh StreamingAssets Projectile-Template Batch

Follow-up after the sound-action batch, focused on the non-guide projectile managed-reference family in `tmp\fresh_audit_unparsed_nonguide_files.txt`.

Read-only subagent evidence plus local metadata checks agreed on this exact current installed-data shape:

- `Beyond.Gameplay.ProjectileTemplateData`: 300 unresolved refs in 300 files.
- Source chunks: `68B3B9B8EB82E88FBFE6A313E6B18FB6.chk` has 229 files, `71FC2E71A9F249B382BF8DAED3BCEE65.chk` has 23 files, and `FBAD673F662CF3EACDDB14A65999F7EF.chk` has 48 files.
- Lengths range from 184 to 388 bytes. 223 payloads are fully covered by raw-word hints; the remaining 77 exceed the hint cap but match the same string/RID length formula.
- Every payload has three component RID links: `ProjectileRootComponentData`, `AbilitySystemData`, and `ProjectileComponentData`.
- Metadata-backed serialized field order is `GameDataWithId.id`, `BaseTemplateData.name/factionIndex`, `EntityTemplateData` scalar fields plus `componentList`, then `ProjectileTemplateData` emit/mount fields plus `SkillDataBundle`.
- Current payloads serialize `EntityTemplateData.bornTag` as one int32 zero, not the two-word gameplay-tag string layout used by other classes.
- `SkillDataBundle.comboSkillConditions` is observed only with count zero. `SkillDataBundle.defaultCmdMapping` is observed only as zero key count plus zero value count. The decoder rejects non-empty forms instead of inventing element schemas.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Passed `recoveredByRid` into the general `Gameplay.Beyond` managed-reference decoder so decoded component lists can expose linked RID type names.
- Added strict `ProjectileTemplateData` decoding for namespace `Beyond.Gameplay`, class `ProjectileTemplateData`, and payloads at least 160 bytes.
- Decoded the direct template fields, nested `baseTemplate`, nested `entityTemplate`, component RID list, and the observed `SkillDataBundle` fields.
- Added strict empty-list helpers for `comboSkillConditions` and `defaultCmdMapping` key/value lists; any nonzero count falls back to the existing marker path.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\projectile_template_validation_after3\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\projectile_template_validation_filters\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\projectile_template_validation_after3\71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\projectile_template_validation_filters\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\projectile_template_validation_after3\FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\projectile_template_validation_filters\names_3_FBAD673F.txt
```

Build result: success with `0` warnings and `0` errors. The three targeted exports covered all 300 projectile-template files, exited with code 0, and emitted no warning/error output.

Projectile family in the final targeted validation set:

| Class | Fresh audit `$unparsed` | Final `$unparsed` | Final decoded | Final partial |
| --- | ---: | ---: | ---: | ---: |
| `Beyond.Gameplay.ProjectileTemplateData` | 300 | 0 | 300 | 0 |
| `Beyond.Gameplay.Core.ProjectileRootComponentData` | 300 | 0 | 300 | 0 |
| `Beyond.Gameplay.Core.AbilitySystemData` | 0 | 0 | 300 | 300 |
| `Beyond.Gameplay.Core.ProjectileComponentData` | 300 | 300 | 0 | 0 |

Resolved `$unparsed` refs attributable to this batch: 300 `ProjectileTemplateData` refs. `ProjectileRootComponentData` is also decoded in the same validation output due to the previous projectile-root batch. Current classification: `ProjectileTemplateData` is now understood as a normal serialized managed-reference payload, not missing VFS/AB bytes and not encryption. The remaining projectile blocker is `ProjectileComponentData`; its collider/effect/audio/list/movement sections still need a staged schema proof before decoding.

Next candidate from the parallel read-only audit: `Beyond.Gameplay.WikiModelSpawnData` has 129 unresolved refs in one file and a metadata-backed layout that accounts for all observed lengths. `WeaponDecoEffectData` is likely but should wait for raw-byte validation of the longest 800-byte payload before being claimed exact.

## 2026-06-29 Twentieth Fresh StreamingAssets Wiki-Model Batch

Follow-up after the projectile-template batch. Work focused on the unresolved `Beyond.Gameplay.WikiModelSpawnData` managed references in `tmp\fresh_json_audit_20260629_streaming\MonoBehaviour\WikiModelConfig_p9149561BFAD103BF.json`.

Evidence used:

- The fresh audit file contains 129 `Beyond.Gameplay.WikiModelSpawnData` refs and 5 separate unresolved `Beyond.Gameplay.WikiWeaponData` refs.
- All 129 Wiki model spawn refs come from `StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk` in `WikiModelConfig`.
- Payload length distribution: `44 x106`, `124 x2`, `128 x9`, `136 x2`, `140 x5`, `144 x1`, `152 x3`, `512 x1`.
- Effect-count distribution from raw word hints: `0 x106`, `1 x22`, `5 x1`.
- Local IL2CPP metadata and the serialized TypeTree agree on `WikiModelSpawnData` fields: `position`, `rotation`, `scale`, `cameraDistance`, `effects`.
- Local IL2CPP metadata and the serialized TypeTree agree on `WikiModelEffectData` fields: `name`, `mountPoint`, `followScale`, `followRotation`, `offset`, `rotation`, `scale`.
- The longest 512-byte payload decodes into five plausible effect records such as `P_palesent_standby_head` / `Ring_Bone` and ring effects mounted to `Bip001_*` bones.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added strict `WikiModelSpawnData` decoding under the existing `Gameplay.Beyond` managed-reference decoder.
- Decoded `position`, `rotation`, `scale`, `cameraDistance`, and `effects`.
- Added `ReadWikiModelEffectList` and `ReadWikiModelEffectData` helpers.
- Effect-list guard requires a non-negative count, at most 16 entries, and enough remaining bytes for the minimum 52-byte effect shape before reading variable-length strings. Existing reader guards still reject invalid ASCII strings, bad bool32 values, NaN/Infinity floats, and incomplete payloads.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\wiki_model_spawn_validation_after\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\wiki_model_spawn_validation_filters\names.txt
```

The targeted export covered `WikiModelConfig`, exited with code 0, and emitted no warning/error output. The build succeeded; the first build in this batch showed the existing 14 AnimeStudio/Utility warnings and no errors.

Before/after for the targeted file:

| Class | Fresh audit `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.WikiModelSpawnData` | 129 | 0 | 129 |
| `Beyond.Gameplay.WikiWeaponData` | 5 | 5 | 0 |

Resolved `$unparsed` refs attributable to this batch: 129 `WikiModelSpawnData` refs. Current classification: these were normal serialized managed-reference payloads with TypeTree/IL2CPP-backed fields, not missing VFS/AB bytes and not encryption. Remaining Wiki work is `WikiWeaponData`; the parallel audits are also looking at `ProjectileComponentData` and raw validation for WeaponDecoEffectData.

## 2026-06-29 Twenty-First Fresh StreamingAssets Wiki-Weapon Batch

Follow-up after the Wiki model spawn batch. Work focused on the five remaining unresolved `Beyond.Gameplay.WikiWeaponData` managed references in `WikiModelConfig`.

Evidence used:

- The same fresh audit file, `tmp\fresh_json_audit_20260629_streaming\MonoBehaviour\WikiModelConfig_p9149561BFAD103BF.json`, contains 5 `Beyond.Gameplay.WikiWeaponData` refs.
- Payload lengths are `48 x4` and `92 x1`; no string hints are present.
- Local IL2CPP metadata exposes exactly one `WikiWeaponData` field: `spawnDataList`.
- The serialized word layout is `spawnDataList.count` followed by nested `WikiModelSpawnData` records. Four payloads have count 1 (`4 + 44` bytes); one payload has count 2 (`4 + 44 + 44` bytes).
- The nested spawn records reuse the Wiki model spawn layout proven in the previous batch. In the current five weapon payloads, nested `effects` lists are empty.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Refactored Wiki model spawn field reading into `ReadWikiModelSpawnData` so top-level `WikiModelSpawnData` and nested weapon entries share the same strict layout.
- Added strict `WikiWeaponData` decoding under the existing `Gameplay.Beyond` managed-reference decoder.
- Added `ReadWikiModelSpawnDataList` with a non-negative count, maximum 16 entries, and a minimum 44-byte per-entry remaining-size guard.
- Kept existing string, bool32, finite-float, and complete-payload guards for nested spawn/effect records.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\wiki_weapon_validation_after\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\wiki_model_spawn_validation_filters\names.txt
```

The targeted export covered `WikiModelConfig`, exited with code 0, and emitted no warning/error output. The build succeeded with the existing 14 AnimeStudio/Utility warnings and no errors.

Before/after for the targeted file:

| Class | Fresh audit `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.WikiModelSpawnData` | 129 | 0 | 129 |
| `Beyond.Gameplay.WikiWeaponData` | 5 | 0 | 5 |

Resolved `$unparsed` refs attributable to this batch: 5 `WikiWeaponData` refs. Combined with the previous batch, `WikiModelConfig` now has zero unresolved managed-reference markers in the targeted validation output. Current classification: `WikiWeaponData` is a normal serialized managed-reference payload containing nested `WikiModelSpawnData` records, not missing VFS/AB bytes and not encryption.

## 2026-06-29 Twenty-Second Fresh StreamingAssets Weapon-Deco Batch

Follow-up after the Wiki batches. Work focused on `Beyond.Gameplay.WeaponDecoEffectData` in `tmp\fresh_json_audit_20260629_streaming\MonoBehaviour\WeaponDecoEffectConfig_p684AA56161A3604F.json`.

Evidence used:

- The fresh audit file contains 73 `Beyond.Gameplay.WeaponDecoEffectData` refs, all unresolved before this batch.
- All 73 refs come from `StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk` in `WeaponDecoEffectConfig`.
- Payload length distribution: `128 x1`, `136 x1`, `144 x3`, `152 x26`, `160 x1`, `168 x8`, `176 x17`, `184 x3`, `188 x5`, `248 x1`, `272 x1`, `288 x1`, `496 x1`, `512 x1`, `528 x2`, `800 x1`.
- Local IL2CPP metadata exposes `WeaponDecoEffectData.gemDeco` and `WeaponDecoEffectData.gemMaxDeco`.
- Nested metadata exposes `DecoData.effects`, `DecoData.vfxMaterials`, and `EffectData.name`, `EffectData.mountPoint`, `EffectData.offset`.
- The previous audit could fully parse 66 of 73 refs from preserved raw-word hints. The seven larger refs exceeded the 64-word hint cap, so this batch relied on live targeted export validation against original bytes.
- The 800-byte `wpn_funnel_0003` payload validates as two six-effect deco lists: `gemDeco` contains `P_ui_wpn_funnel_0003_01_1_*` effects and `gemMaxDeco` contains `P_ui_wpn_funnel_0003_01_2_*` effects, mounted to `Bone_part_*` points.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added strict `WeaponDecoEffectData` decoding under the existing `Gameplay.Beyond` managed-reference decoder.
- Decoded `gemDeco` and `gemMaxDeco` as `DecoData` records.
- Added `ReadWeaponDecoData`, `ReadWeaponDecoEffectList`, and `ReadWeaponDecoEffectData` helpers.
- Effect-list guards require non-negative counts, at most 32 entries, and enough remaining bytes for the minimum 20-byte effect shape before variable-length strings. `vfxMaterials` uses the existing bounded string-list reader with max 32 entries.
- Existing reader guards reject invalid ASCII strings, NaN/Infinity floats, bad ranges, and incomplete payloads; any mismatch falls back to the marker path instead of suppressing errors.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\weapon_deco_validation_after\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\weapon_deco_validation_filters\names.txt
```

The targeted export covered `WeaponDecoEffectConfig`, exited with code 0, and emitted no warning/error output. The build succeeded with the existing 14 AnimeStudio/Utility warnings and no errors.

Before/after for the targeted file:

| Class | Fresh audit `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.WeaponDecoEffectData` | 73 | 0 | 73 |

Resolved `$unparsed` refs attributable to this batch: 73 `WeaponDecoEffectData` refs. Current classification: these are normal serialized managed-reference payloads backed by local IL2CPP metadata, not missing VFS/AB bytes and not encryption. `ProjectileComponentData` remains intentionally unresolved until complete raw payload extraction proves its long tail layout.

## 2026-06-29 Twenty-Third Fresh StreamingAssets Projectile-Component Raw-Payload Batch

Follow-up after the weapon-deco decoder batch. Work focused on the largest still-unresolved managed-reference family, `Beyond.Gameplay.Core.ProjectileComponentData`.

Read-only subagent conclusion:

- A full strict `ProjectileComponentData` decoder is not yet defensible from the old fresh-audit JSON alone.
- The existing heuristic JSON capped raw-word hints at 64 dwords, while `ProjectileComponentData` payloads are 1452-3784 bytes long.
- The prefix and several movement/effect landmarks are plausible, but the long tail is not fully proven. Returning `$decoded` now would suppress warnings on an unproven schema.
- The exporter already has a safer path for exact bytes: raw JSON sidecars can be enabled with `ANIMESTUDIO_EXPORT_JSON_RAW=1`, and recovered managed-reference entries already carry `dataOffset` and `dataLength`.

Probe run:

```bat
set ANIMESTUDIO_EXPORT_JSON_RAW=1
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\projectile_component_raw_probe\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\projectile_template_validation_filters\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\projectile_component_raw_probe\71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\projectile_template_validation_filters\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\projectile_component_raw_probe\FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\projectile_template_validation_filters\names_3_FBAD673F.txt
```

The three targeted exports covered all 300 projectile files, exited with code 0, and emitted no warning/error output. Raw sidecars were written next to the probe JSON files under `tmp\projectile_component_raw_probe\`.

Extraction output:

- Manifest: `tmp\projectile_component_payload_slices\manifest.jsonl`
- Summary: `tmp\projectile_component_payload_slices\summary.json`
- Payload binaries: `tmp\projectile_component_payload_slices\payloads\*.bin`
- Extracted payload count: 300
- Sidecar/hash/offset errors: 0
- Chunk distribution: `68B3B9B8EB82E88FBFE6A313E6B18FB6.chk` has 229 payloads, `71FC2E71A9F249B382BF8DAED3BCEE65.chk` has 23 payloads, and `FBAD673F662CF3EACDDB14A65999F7EF.chk` has 48 payloads.

The extraction verified each JSON sidecar SHA-256 against `$animestudio.rawDataSha256`, then sliced each `ProjectileComponentData` payload using `dataOffset` and `dataLength`, and wrote a per-payload SHA-256 into the JSONL manifest.

Targeted export marker status after this probe:

| Class | Final `$unparsed` | Final decoded |
| --- | ---: | ---: |
| `Beyond.Gameplay.ProjectileTemplateData` | 0 | 300 |
| `Beyond.Gameplay.Core.ProjectileRootComponentData` | 0 | 300 |
| `Beyond.Gameplay.Core.AbilitySystemData` | 0 | 300 |
| `Beyond.Gameplay.Core.ProjectileComponentData` | 300 | 0 |

This is intentional: the raw-payload batch does not reduce warning counts by itself. It preserves the `ProjectileComponentData` unresolved markers while providing exact binary evidence for the next parser iteration. Current classification: the blocker is no longer missing bytes; it is an unproven long managed-reference schema requiring full-payload layout work.

## 2026-06-29 Twenty-Fourth Fresh StreamingAssets Weapon-RID-Wrapper Batch

Follow-up after the projectile-component raw-payload batch. Work focused on the small weapon RID-wrapper family from the stale non-guide audit.

Evidence used:

- `Beyond.Gameplay.View.WeaponComponentData`: 28 refs across 28 files in three chunks.
- `Beyond.Gameplay.WeaponDataWrapper`: 29 refs across the same 28 files in three chunks.
- Source chunk distribution for the target files: `68B3B9B8EB82E88FBFE6A313E6B18FB6.chk` has 25 files, `71FC2E71A9F249B382BF8DAED3BCEE65.chk` has 1 file, and `FBAD673F662CF3EACDDB14A65999F7EF.chk` has 2 files.
- Payloads are exact `4 + 8*N` RID-list shapes. `WeaponComponentData` lengths are `12 x27` and `20 x1`; `WeaponDataWrapper` lengths range from 12 to 108 and match the observed RID count.
- Local IL2CPP metadata exposes `WeaponComponentData.weaponCfg` and `WeaponDataWrapper.dataList` as the only fields for these classes.
- RID hints show `WeaponComponentData.weaponCfg` links to one or two `WeaponDataWrapper` refs; `WeaponDataWrapper.dataList` links to `WeaponData` and sometimes `StaticWeaponData` refs.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added strict `Beyond.Gameplay.View.WeaponComponentData` decoding under the view managed-reference decoder.
- Added strict `Beyond.Gameplay.WeaponDataWrapper` decoding under the general `Gameplay.Beyond` managed-reference decoder.
- Both decoders use the existing `ReadPayloadRidLinkList` helper with max 16 entries and `EnsureComplete()`, so invalid counts, bad RID ranges, or extra trailing bytes fall back to the marker path.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\weapon_wrapper_validation_after\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\weapon_wrapper_validation_filters\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\weapon_wrapper_validation_after\71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\weapon_wrapper_validation_filters\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\weapon_wrapper_validation_after\FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\weapon_wrapper_validation_filters\names_3_FBAD673F.txt
```

The targeted exports covered all 28 weapon-wrapper files, exited with code 0, and emitted no warning/error output. The build succeeded with the existing 14 AnimeStudio/Utility warnings and no errors.

Before/after for the targeted files:

| Class | Fresh audit `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.View.WeaponComponentData` | 28 | 0 | 28 |
| `Beyond.Gameplay.WeaponDataWrapper` | 29 | 0 | 29 |
| `Beyond.Gameplay.WeaponData` | 45 | 45 | 0 |
| `Beyond.Gameplay.StaticWeaponData` | 41 | 41 | 0 |

Resolved `$unparsed` refs attributable to this batch: 57 wrapper refs. Current classification: the wrapper classes are normal serialized managed-reference RID lists backed by local IL2CPP metadata, not missing VFS/AB bytes and not encryption. `WeaponData` and `StaticWeaponData` remain separate unresolved payloads and are under parallel read-only audit.

## 2026-06-29 Twenty-Fifth Fresh StreamingAssets Weapon-Data Batch

Follow-up after the weapon RID-wrapper batch. Work focused on the payload records linked by `WeaponDataWrapper.dataList`.

Read-only audit conclusions:

- `Beyond.Gameplay.WeaponData`: 45 refs across 28 files in three chunks. Payload lengths are `44 x41` and `52 x4`.
- `WeaponData` shape is `weaponIndex:int32`, `vfxKey:aligned string`, `weaponScale:float32`, then `showWhenIdle`, `idleMountPoint`, `showWhenFight`, `fightMountPoint`, `overrideAnimation`, and `overrideController:PPtr`.
- Local IL2CPP metadata exposes `WeaponDataBase.weaponIndex/vfxKey/weaponScale/<weaponPath>k__BackingField` plus the six `WeaponData` fields. The observed standalone payloads omit `weaponPath`; the decoder treats extra bytes as a mismatch.
- `Beyond.Gameplay.StaticWeaponData`: 41 refs across 15 of the same 28 files in three chunks. Payload lengths are `88 x36`, `100 x1`, `104 x1`, `120 x1`, and `124 x2`.
- `StaticWeaponData` shape is `weaponIndex:int32`, `vfxKey:aligned string`, `weaponScale:float32`, `_weaponPath:aligned string`, then the same visibility and override tail.
- Local IL2CPP metadata exposes `StaticWeaponDataBase._weaponPath` plus the six `StaticWeaponData` fields.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added strict `Beyond.Gameplay.WeaponData` decoding under the general `Gameplay.Beyond` managed-reference decoder.
- Added strict `Beyond.Gameplay.StaticWeaponData` decoding under the same decoder.
- Both decoders require exact namespace/class identity, strict aligned ASCII strings, finite floats, bool32 fields, readable PPtrs, fixed tail byte counts after variable strings, and `EnsureComplete()`. Any mismatch falls back to the existing `$unparsed` marker path.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\weapon_static_validation_after\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\weapon_wrapper_validation_filters\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\weapon_static_validation_after\71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\weapon_wrapper_validation_filters\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\weapon_static_validation_after\FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\weapon_wrapper_validation_filters\names_3_FBAD673F.txt
```

The targeted exports covered all 28 weapon files, exited with code 0, and emitted no warning/error output. The rebuild succeeded with 0 warnings and 0 errors.

Before/after for the targeted files:

| Class | Fresh audit `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.View.WeaponComponentData` | 28 | 0 | 28 |
| `Beyond.Gameplay.WeaponDataWrapper` | 29 | 0 | 29 |
| `Beyond.Gameplay.WeaponData` | 45 | 0 | 45 |
| `Beyond.Gameplay.StaticWeaponData` | 41 | 0 | 41 |

Resolved `$unparsed` refs attributable to this batch: 86 weapon data refs. Current classification: these are normal serialized managed-reference payloads backed by local IL2CPP metadata, not missing VFS/AB bytes and not encryption. The remaining unresolved refs in these 28 files are unrelated character/core/view component classes and condition payloads.

## 2026-06-29 Twenty-Sixth Fresh StreamingAssets Small-Component And AI Batch

Follow-up after the weapon-data decoder batch. Work focused on compact managed-reference payloads that had local IL2CPP metadata field names and exact targeted validation coverage.

Evidence used:

- Current baseline exports under `tmp\next_decoder_baseline_current_20260629\` confirmed the target classes were still unresolved before this batch.
- Local metadata from `tmp\component_observed_metadata.json` identified fields for `CGData`, `CharacterAIComponentData`, `ObservedComponentData`, `CharHurtAnimComponentData`, `SkeletalMorphComponentData`, and `WaterSensorComponentData`.
- Read-only subagents independently audited compact AI/phase-forbid payloads, `CGData` padding/enums, and `CharacterPivotComponentData` Unity curve payloads.
- Generated targeted name filters live under `tmp\next_decoder_validation_filters_20260629\`.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added strict `CGData` decoding: UTF-8 `name`, `skipType`, and `noSafeZone`, with aligned string-padding, enum-range, and bool32 guards.
- Added strict small component decoding for `CharacterAIComponentData.aiCfg`, `ObservedComponentData.checkTagList/shapeType/center/size/radius`, `CharHurtAnimComponentData` timing floats, `SkeletalMorphComponentData._avatarTag`, and the nine `WaterSensorComponentData` flags/timing fields.
- Added strict `CharacterPivotComponentData` decoding for the IL2CPP field set, including six Unity `AnimationCurve<float>` payloads. This covers both the 120-byte empty-curve character records and the larger movement-setting records with non-empty keyframe curves.
- Added strict compact AI decoding for `ForceSet`, `RandomAdd`, `TargetHasTags`, `HasAttackRangeType`, and `HasFinishToken`.
- Added strict `PhaseForbidParams` decoding for `phaseForbidStyle` and aligned `toastTextId`.
- Guards use exact class identity, exact fixed lengths where the current schema is fixed, bounded non-negative `ForceSet.count`, strict bool32/float/string readers, zero string-padding checks where needed, enum guards where ordinals are known, curve keyframe-count/tail guards, and `EnsureComplete()`.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\component_validation_after_pivot_20260629\cgdata_68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\next_decoder_validation_filters_20260629\cgdata\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\component_validation_after_pivot_20260629\pivot_68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\component_validation_after_pivot_20260629\pivot_71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\component_validation_after_pivot_20260629\pivot_FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_3_FBAD673F.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\component_validation_after_pivot_20260629\ai_compact_68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\next_decoder_validation_filters_20260629\ai_compact\names_1_68B3B9B8.txt
```

The targeted exports covered 34 JSON outputs, exited with code 0, emitted empty warning/error logs, and parsed with 0 JSON failures. The final rebuild succeeded with 0 warnings and 0 errors.

Before/after for the targeted files:

| Class | Baseline `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.CGData` | 36 | 0 | 36 |
| `Beyond.Gameplay.AI.CharacterAIComponentData` | 28 | 0 | 28 |
| `Beyond.Gameplay.Core.ObservedComponentData` | 28 | 0 | 28 |
| `Beyond.Gameplay.Core.CharHurtAnimComponentData` | 28 | 0 | 28 |
| `Beyond.Gameplay.View.SkeletalMorphComponentData` | 28 | 0 | 28 |
| `Beyond.Gameplay.Water.WaterSensorComponentData` | 28 | 0 | 28 |
| `Beyond.Gameplay.View.Animation.CharacterPivotComponentData` | 39 | 0 | 39 |
| `Beyond.Gameplay.AI.ForceSet` | 34 | 0 | 34 |
| `Beyond.Gameplay.AI.RandomAdd` | 13 | 0 | 13 |
| `Beyond.Gameplay.AI.TargetHasTags` | 11 | 0 | 11 |
| `Beyond.Gameplay.AI.HasAttackRangeType` | 9 | 0 | 9 |
| `Beyond.Gameplay.AI.HasFinishToken` | 7 | 0 | 7 |
| `Beyond.Gameplay.PhaseForbidParams` | 22 | 0 | 22 |

Resolved `$unparsed` refs attributable to this batch: 311 refs. Current classification: these are normal serialized managed-reference payloads backed by local IL2CPP metadata, not missing VFS/AB bytes and not encryption. The targeted character files still have unresolved `CharacterTemplateData`, `CharacterRootComponentData`, `CharacterAnimationComponentData`, and several condition/action payloads.

## 2026-06-29 Twenty-Seventh Fresh StreamingAssets Compact AI And Forbid Batch

Follow-up after the small-component batch. Work focused on the remaining unresolved compact AI target filters and forbid-parameter payloads in the three current AI config validation files.

Evidence used:

- Current post-decoder validation under `tmp\component_validation_after_pivot_20260629\ai_compact_68B3\` still had 29 `$unparsed` refs in compact AI/forbid classes.
- Local IL2CPP metadata in `tmp\component_observed_metadata.json` exposed field names for `LongTimeNoIdentity`, `TargetDistance`, `EnemyRankType`, `EnemySubRankType`, `TargetInsideMaxSlotRange`, `ResilienceEmpty`, `GeneralAbilityForbidParams`, and `ForbidParamsWithRadioReason`.
- `GeneralAbilityForbidUseParams` declares no new fields but observed payloads match inherited `GeneralAbilityForbidParams` base fields: `forbidStyle` plus aligned `toastTextId`.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added strict forbid-param decoding for `GeneralAbilityForbidParams`, derived `GeneralAbilityForbidUseParams`, and `ForbidParamsWithRadioReason`.
- Added strict compact AI decoding for `LongTimeNoIdentity`, `ResilienceEmpty`, `TargetDistance`, `EnemyRankType`, `EnemySubRankType`, and `TargetInsideMaxSlotRange`.
- Guards use exact class identity, exact fixed lengths for fixed payloads, bounded forbid-style values, strict bool32/float/string readers, enum guard for `TargetDistance.disType`, and `EnsureComplete()`.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\compact_ai_forbid_validation_after_20260629 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\next_decoder_validation_filters_20260629\ai_compact\names_1_68B3B9B8.txt
```

The targeted export covered 3 JSON outputs, exited with code 0, emitted an empty warning/error log, and parsed with 0 JSON failures. The rebuild succeeded with 0 errors; it reported 14 warnings from unchanged AnimeStudio library files outside this decoder patch.

Before/after for the targeted AI config files:

| Class | Baseline `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.GeneralAbilityForbidUseParams` | 6 | 0 | 6 |
| `Beyond.Gameplay.ForbidParamsWithRadioReason` | 2 | 0 | 2 |
| `Beyond.Gameplay.GeneralAbilityForbidParams` | 2 | 0 | 2 |
| `Beyond.Gameplay.AI.LongTimeNoIdentity` | 6 | 0 | 6 |
| `Beyond.Gameplay.AI.TargetDistance` | 2 | 0 | 2 |
| `Beyond.Gameplay.AI.EnemySubRankType` | 4 | 0 | 4 |
| `Beyond.Gameplay.AI.EnemyRankType` | 2 | 0 | 2 |
| `Beyond.Gameplay.AI.TargetInsideMaxSlotRange` | 4 | 0 | 4 |
| `Beyond.Gameplay.AI.ResilienceEmpty` | 1 | 0 | 1 |

Resolved `$unparsed` refs attributable to this batch: 29 refs. Current classification: these are normal serialized managed-reference payloads backed by local IL2CPP metadata and observed payload bytes, not missing VFS/AB bytes and not encryption. After this batch, the targeted AI config validation files have no remaining `$unparsed` managed-reference refs.

## 2026-06-29 Twenty-Eighth Fresh StreamingAssets Character Animation Batch

Follow-up after the compact AI/forbid batch. Work focused on `Beyond.Gameplay.View.CharacterAnimationComponentData` in the current character validation files.

Evidence used:

- A read-only subagent audited 28 current `CharacterAnimationComponentData` payloads across the three character chunks and confirmed the byte layout.
- Local IL2CPP metadata exposes `_minPivotAngle`, `_relaxTriggerTime`, `_idleTriggerTime`, `_idleAnimCount`, `_fightIdleTimeout`, `_memberFightIdleTimeout`, and `_footStepCfgId`.
- The leading `animationConfigPath` string is not named by the direct IL2CPP fields, but is byte-proven in the current corpus and guarded as `Data/Json/AnimationConfig/*.json`.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added strict `CharacterAnimationComponentData` decoding under the view managed-reference decoder.
- Added a reusable aligned UTF-8 string reader that verifies zero padding bytes after aligned strings.
- Guards require exact `Gameplay.Beyond / Beyond.Gameplay.View / CharacterAnimationComponentData`, word-aligned payload length, bounded path string, finite/ranged floats, bounded non-negative idle animation count, bounded footstep config string, and `EnsureComplete()`.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\character_animation_validation_after_20260629\pivot_68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\character_animation_validation_after_20260629\pivot_71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\character_animation_validation_after_20260629\pivot_FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_3_FBAD673F.txt
```

The targeted exports covered 30 JSON outputs, exited with code 0, emitted empty warning/error logs, and parsed with 0 JSON failures. The rebuild succeeded with 0 errors; it reported 14 warnings from unchanged AnimeStudio library files outside this decoder patch.

Before/after for the targeted files:

| Class | Baseline `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.View.CharacterAnimationComponentData` | 28 | 0 | 28 |

Resolved `$unparsed` refs attributable to this batch: 28 refs. Current classification: these are normal serialized managed-reference payloads backed by local IL2CPP metadata plus byte-proven path data, not missing VFS/AB bytes and not encryption. The same character validation files still have unresolved `CharacterTemplateData`, `CharacterRootComponentData`, and condition/action payloads.

## 2026-06-29 Twenty-Ninth Fresh StreamingAssets Character Template Batch

Follow-up after the character animation batch. Work focused on `Beyond.Gameplay.CharacterTemplateData` in the same current character validation files.

Evidence used:

- A read-only subagent audited 28 current `CharacterTemplateData` payloads across the three character chunks and confirmed the byte layout.
- Local IL2CPP metadata supports the inherited `GameDataWithId` / `BaseTemplateData` / `EntityTemplateData` field order plus `CharacterTemplateData.animConfigPath` and `BodyTypeDef` fields.
- The current corpus uses exactly 26 component RID links per character template. Two records carry an optional born `GameplayTag`; the rest serialize the absent-tag flag only.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added strict `CharacterTemplateData` decoding under the general gameplay managed-reference decoder.
- Added a strict zero-padding `GameplayTag` reader for the optional born tag path used by this layout.
- Guards require exact `Gameplay.Beyond / Beyond.Gameplay / CharacterTemplateData`, word-aligned payload length, `chr_` id prefix, strict aligned UTF-8 strings with zero padding, bool32 flags, bounded lifecycle/fade floats, exactly 26 component RID links, an `Assets/*.asset` animation config path, and `EnsureComplete()`.
- `bodyType` and `CustomId` are preserved as raw hash-style int32 values because their enum/domain is not yet identified.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\character_template_validation_after_20260629\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\character_template_validation_after_20260629\71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\character_template_validation_after_20260629\FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_3_FBAD673F.txt
```

The targeted exports covered 30 JSON outputs, exited with code 0, emitted no console warning/error output, and parsed with 0 JSON failures in follow-up counting. The rebuild succeeded with 0 errors; it reported 14 warnings from unchanged AnimeStudio library files outside this decoder patch.

Before/after for the targeted files:

| Class | Baseline `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.CharacterTemplateData` | 28 | 0 | 28 |

Resolved `$unparsed` refs attributable to this batch: 28 refs. Current classification: these are normal serialized managed-reference payloads backed by local IL2CPP metadata plus byte-proven current corpus invariants, not missing VFS/AB bytes and not encryption. The same character validation files still have unresolved `CharacterRootComponentData` and condition/action payloads.

## 2026-06-29 Thirtieth Fresh StreamingAssets Core Action And Condition Batch

Follow-up after the character template batch. Work focused on the subagent-proven `Beyond.Gameplay.Core` action/condition payloads in the current character validation files, while deliberately leaving `TargetSettings`-based payloads unresolved.

Evidence used:

- Two read-only subagents audited the current character outputs and separated strict layouts from unsafe target/tail layouts.
- `CheckDamageDecorateMask/Data` and `CheckBuffIdInContext/Data` have complete layouts after the inherited `AbilityActionData` prefix.
- `CheckSpellInflictionType/Data`, `CheckPhysicalInflictionType/Data`, `CompareFloat/Data`, `IfElseAction/IfElseActionData`, `NotNextCheckAction/Data`, and `ReturnFalseAction/Data` have complete layouts in the current corpus.
- Validation corrected one audit detail: `CompareFloat/Data` `BlackboardDouble` records serialize an aligned key string even when `useBlackboardKey` is false; the observed false branch carries an empty key string.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Passed recovered managed-reference RID metadata into the core gameplay decoder so `IfElseAction` sequence action RID links can be exported with target type information.
- Added strict decoding for `CheckDamageDecorateMask/Data`, `CheckBuffIdInContext/Data`, `CheckSpellInflictionType/Data`, `CheckPhysicalInflictionType/Data`, `CompareFloat/Data`, `IfElseAction/IfElseActionData`, `NotNextCheckAction/Data`, and `ReturnFalseAction/Data`.
- Added strict helpers for the inherited `AbilityActionData` prefix, zero-padded ASCII strings/lists, zero-padded gameplay tag lists and tag queries, `BlackboardDouble`, `SequenceActionData`, and bounded int32 masks.
- Guards use exact namespace/class checks, exact fixed lengths where proven, word alignment for variable layouts, bounded counts, bool32 readers, enum/range guards, RID-link preservation, strict zero-padding checks, and `EnsureComplete()`.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\action_condition_validation_after_20260629_v2\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\action_condition_validation_after_20260629_v2\71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\action_condition_validation_after_20260629_v2\FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_3_FBAD673F.txt
```

The final rebuild after the `CompareFloat` correction reported 0 warnings and 0 errors. The targeted exports covered 30 JSON outputs, exited with code 0, emitted no console warning/error output, and parsed with 0 JSON failures. Structural reference counting was used so heuristic RID-link mentions were not counted as actual managed-reference entries.

Before/after for the targeted files:

| Class | Baseline `$unparsed` | Final `$unparsed` | Final decoded |
| --- | ---: | ---: | ---: |
| `Beyond.Gameplay.Core.Conditions.CheckDamageDecorateMask/Data` | 12 | 0 | 12 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffIdInContext/Data` | 12 | 0 | 12 |
| `Beyond.Gameplay.Core.Conditions.CheckSpellInflictionType/Data` | 5 | 0 | 5 |
| `Beyond.Gameplay.Core.Conditions.CheckPhysicalInflictionType/Data` | 1 | 0 | 1 |
| `Beyond.Gameplay.Core.CompareFloat/Data` | 3 | 0 | 3 |
| `Beyond.Gameplay.Core.IfElseAction/IfElseActionData` | 3 | 0 | 3 |
| `Beyond.Gameplay.Core.NotNextCheckAction/Data` | 2 | 0 | 2 |
| `Beyond.Gameplay.Core.ReturnFalseAction/Data` | 1 | 0 | 1 |

Resolved `$unparsed` refs attributable to this batch: 39 refs. Current classification: these are normal serialized managed-reference payloads backed by local IL2CPP metadata plus byte-proven current corpus invariants, not missing VFS/AB bytes and not encryption.

Explicitly left unresolved because full layouts are not yet proven:

| Class | Current `$unparsed` | Reason |
| --- | ---: | --- |
| `Beyond.Gameplay.Core.Conditions.CheckObjectTypeMatch/Data` | 22 | depends on unresolved `TargetSettings` layout |
| `Beyond.Gameplay.Core.Conditions.CheckMainCharacterCondition/Data` | 7 | depends on unresolved `TargetSettings` layout |
| `Beyond.Gameplay.Core.Conditions.CheckTargetsEqual/Data` | 6 | depends on unresolved `TargetSettings` layout |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNum/Data` | 5 | depends on unresolved `TargetSettings` layout |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag/Data` | 5 | depends on unresolved `TargetSettings` layout |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 | target/buff tail blocks are not byte-proven yet |
| `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data` | 2 | target/tail blocks are not byte-proven yet |
| `Beyond.Gameplay.Core.StoreBuffCount/Data` | 1 | target/tail blocks are not byte-proven yet |

A separate read-only audit confirmed no strict full decoder is defensible yet for `CreateBuffAction/Data`, `ModifyDynamicBlackboard/Data`, or `StoreBuffCount/Data`. Local IL2CPP metadata names their direct fields, but the shared `TargetSettings` and selector-data sublayouts are still ambiguous around `rid=-2` sentinels and counted/list slots. The next useful probe is a raw full-payload hex/offset trace for these 8 unique payloads, not a decoded export path.

## 2026-06-29 Thirty-First Fresh StreamingAssets TargetSettings Diagnostic Trace Batch

Follow-up after the core action/condition batch. Work focused on evidence collection for the unresolved `TargetSettings` and buff-action layouts instead of promoting unsafe decoders.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added diagnostic-only full raw payload traces for the unresolved target/buff managed-reference families.
- The diagnostic path only runs on the still-unparsed fallback path and keeps `$unparsed` / `$heuristic` set, so no payload is treated as understood by this batch.
- Each selected entry now carries `diagnosticFullPayloadHex` plus a complete `diagnosticRawWordTrace` with relative/absolute offsets, int32/hex values, finite float interpretations, and printable ASCII word hints.
- The trace deliberately removes the prior 64-word heuristic cap for these families, including the 280-byte `CheckBuffStackNumByTag/Data` case.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\targetsettings_trace_after_20260629\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\targetsettings_trace_after_20260629\71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\targetsettings_trace_after_20260629\FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_3_FBAD673F.txt
```

The targeted exports covered 30 JSON outputs, exited with code 0, emitted no console warning/error output, and parsed with 0 JSON failures. The final rebuild after source cleanup reported 0 warnings and 0 errors.

Diagnostic coverage for the targeted files:

| Class | Entries | Unique payloads | Payload lengths | Still `$unparsed` | Missing diagnostic trace |
| --- | ---: | ---: | --- | ---: | ---: |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 | 5 | 244, 268 | 5 | 0 |
| `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data` | 2 | 2 | 164 | 2 | 0 |
| `Beyond.Gameplay.Core.StoreBuffCount/Data` | 1 | 1 | 184 | 1 | 0 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNum/Data` | 5 | 5 | 168 | 5 | 0 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag/Data` | 5 | 5 | 196, 208, 212, 280 | 5 | 0 |
| `Beyond.Gameplay.Core.Conditions.CheckMainCharacterCondition/Data` | 7 | 4 | 116, 124 | 7 | 0 |
| `Beyond.Gameplay.Core.Conditions.CheckObjectTypeMatch/Data` | 22 | 10 | 120, 128 | 22 | 0 |
| `Beyond.Gameplay.Core.Conditions.CheckTargetsEqual/Data` | 6 | 6 | 224, 232 | 6 | 0 |

Compact trace summary was written to `tmp/targetsettings_trace_after_20260629/targetsettings_trace_compact_summary.txt` for local follow-up. The dominant repeated structure is a shared target selector block with optional aligned strings such as `trigger` / `target`, three `rid=-2` sentinel slots, and long zero-padded regions. `CheckTargetsEqual/Data` appears to contain two target selector blocks; buff-count and buff-action classes append buff/tag/blackboard fields after the same target selector pattern.

Current classification: these bytes are present in the exported AB/MonoBehaviour payloads and are not evidence of missing VFS bytes or encryption. They remain not fully understood because the shared `TargetSettings` / selector-data sublayout and the meaning of its null/sentinel/list slots are not yet byte-proven. The next safe implementation step is a candidate `TargetSettings` parser that can parse into a clearly named diagnostic object and preserve unknown slots, but it should not mark these families fully decoded until the selector-data layout is proven against more current payloads.

## 2026-06-29 Thirty-Second Fresh StreamingAssets TargetSettings Structured Diagnostic Batch

Follow-up after the full raw TargetSettings trace batch. Two read-only subagents audited the raw trace and local IL2CPP metadata. The shared conclusion was that `TargetSettings` byte boundaries are now clear for the observed 0x64/0x6c forms, but the selector-data count/flag, late RID slots, and eight-word suffix are not semantically named well enough to mark parent payloads fully decoded.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added `diagnosticStructuredLayout` only on the existing `$unparsed` fallback path for unresolved `TargetSettings` families.
- Kept `$unparsed` and `$heuristic` intact. This batch deliberately does not reduce warning/error counts or claim full decode.
- The structured diagnostic now parses:
  - inherited `AbilityActionData` prefix;
  - metadata-backed `TargetSettings` front fields through `selectorData`;
  - selector RID links, including positive references such as `Selector/CharacterTeamFinder/Data` and `Selector/MainCharacterValidator/Data`;
  - unresolved selector count/flag, late RID slots, and suffix words as raw/hash fields with layout notes;
  - candidate fixed tails for `CheckBuffStackNum`, `CheckBuffStackNumByTag`, `ModifyDynamicBlackboard`, and `StoreBuffCount` where the current bytes are structurally proven but some generic/list semantics remain unresolved.
- `CreateBuffAction/Data` remains raw-trace only because its `buffs` list body and post-target tail are not yet proven.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\targetsettings_structured_after_20260629\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\targetsettings_structured_after_20260629\71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\targetsettings_structured_after_20260629\FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_3_FBAD673F.txt
```

The rebuild succeeded with 0 errors and 14 unchanged warnings from existing AnimeStudio projects. The targeted exports covered 30 JSON outputs, exited with code 0, emitted no console warning/error output, and parsed with 0 JSON failures.

Structured diagnostic coverage for the targeted files:

| Class | Entries | Still `$unparsed` | Full raw trace | Structured diagnostic |
| --- | ---: | ---: | ---: | ---: |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNum/Data` | 5 | 5 | 5 | 5 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag/Data` | 5 | 5 | 5 | 5 |
| `Beyond.Gameplay.Core.Conditions.CheckMainCharacterCondition/Data` | 7 | 7 | 7 | 7 |
| `Beyond.Gameplay.Core.Conditions.CheckObjectTypeMatch/Data` | 22 | 22 | 22 | 22 |
| `Beyond.Gameplay.Core.Conditions.CheckTargetsEqual/Data` | 6 | 6 | 6 | 6 |
| `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data` | 2 | 2 | 2 | 2 |
| `Beyond.Gameplay.Core.StoreBuffCount/Data` | 1 | 1 | 1 | 1 |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 | 5 | 5 | 0 |

Current classification: this is real progress toward understanding, not warning suppression. The bytes are structured enough to expose TargetSettings offsets and RID links in exported JSON, including non-null selector references. They are still not fully understood because several selector-data fields and suffix words are unnamed. The next safe target is either (a) prove the selector-data suffix fields from IL2CPP/MemoryPack metadata or (b) isolate and decode `CreateBuffAction/Data` list/tail bytes with the same diagnostic-first approach.

## 2026-06-29 Thirty-Third Fresh StreamingAssets CreateBuffAction Structured Diagnostic Batch

Follow-up after the TargetSettings structured diagnostic batch. Work focused on the last raw-only class in the current target/buff cluster: `Beyond.Gameplay.Core.CreateBuffAction/Data`.

Evidence used:

- Local byte extraction over the five current `CreateBuffAction/Data` payloads in `tmp/targetsettings_structured_after_20260629`.
- Existing IL2CPP field-order evidence for `CreateBuffAction/Data`: inherited `AbilityActionData`, `buffs`, `count: BlackboardDouble`, `targetSettings: TargetSettings`, `buffSource`, `contextKey`, and unresolved tail fields including `inheritSkillIdList` and `buffIconDurationSourceSetting`.
- Current `TargetSettings` structured diagnostics from the previous batch.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added `CreateBuffAction/Data` to the existing `diagnosticStructuredLayout` path only.
- Kept `$unparsed` and `$heuristic` intact. This still does not claim a full decode.
- The structured diagnostic now parses the stable leading section:
  - inherited `AbilityActionData` prefix;
  - candidate `buffs` list: count-prefixed aligned buff-id string list followed by four reserved zero words;
  - `countCandidate` as the same `BlackboardDouble` layout used by previously decoded float comparisons;
  - `targetSettings` through the partial TargetSettings diagnostic parser;
  - `buffSourceCandidate` and `contextKeyCandidate`.
- The remaining nine post-context words are preserved as `tailWords` because `inheritSkillIdList`, the boolean tail, and `buffIconDurationSourceSetting` are not semantically proven enough for a full decoder.

Validation details:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\createbuff_structured_after_20260629\68B3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_1_68B3B9B8.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\createbuff_structured_after_20260629\71FC --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_2_71FC2E71.txt
AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\createbuff_structured_after_20260629\FBAD --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\next_decoder_validation_filters_20260629\character_pivot\names_3_FBAD673F.txt
```

The rebuild succeeded with 0 errors and 14 unchanged warnings from existing AnimeStudio projects. The targeted exports covered 30 JSON outputs, exited with code 0, emitted no console warning/error output, and parsed with 0 JSON failures.

Structured diagnostic coverage for the targeted files now covers the full current target/buff cluster:

| Class | Entries | Still `$unparsed` | Full raw trace | Structured diagnostic |
| --- | ---: | ---: | ---: | ---: |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 | 5 | 5 | 5 |
| `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data` | 2 | 2 | 2 | 2 |
| `Beyond.Gameplay.Core.StoreBuffCount/Data` | 1 | 1 | 1 | 1 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNum/Data` | 5 | 5 | 5 | 5 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag/Data` | 5 | 5 | 5 | 5 |
| `Beyond.Gameplay.Core.Conditions.CheckMainCharacterCondition/Data` | 7 | 7 | 7 | 7 |
| `Beyond.Gameplay.Core.Conditions.CheckObjectTypeMatch/Data` | 22 | 22 | 22 | 22 |
| `Beyond.Gameplay.Core.Conditions.CheckTargetsEqual/Data` | 6 | 6 | 6 | 6 |

Current classification: this is still diagnostic progress, not warning suppression. We now have structured evidence for all 53 current target/buff entries while preserving the fact that all 53 are not fully understood. The next evidence needed is semantic proof for `CreateBuffAction` tail words and `TargetSettings` selector/suffix fields, or a broader scan that finds more variants for these same classes.

## 2026-06-29 Thirty-Fourth Fresh StreamingAssets CharacterRootComponentData Batch

Follow-up after the TargetSettings/CreateBuffAction diagnostic batch. Work focused on the largest remaining non-TargetSettings bucket in the current 30-file character validation slice: `Beyond.Gameplay.Core.CharacterRootComponentData`.

Evidence used:

- Current validation inventory showed 28 unresolved `CharacterRootComponentData` refs across 28 character files, with payload lengths from 640 to 1800 bytes.
- A first diagnostic-only patch added full raw payload hex/word traces for unresolved `CharacterRootComponentData` without changing `$unparsed` status.
- Targeted `--map_op All` exports over the same three StreamingAssets chunks (`68B3...`, `71FC...`, `FBAD...`) produced 30 MonoBehaviour JSON files with 0 JSON parse failures and 28/28 CharacterRoot full-payload traces.
- Raw-byte analysis proved the shared prefix: `locatorIds` count/list, matching `locatorNames` count/list, then an `unknown0` int32, then root transform records using the same string + seven-float shape already used by the existing `EnemyRootComponentData` decoder.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added an inferred `CharacterRootComponentData` decoder beside the existing `EnemyRootComponentData` decoder.
- The decoder reads locator IDs, locator names, `unknown0`, up to 16 transform records, and preserves the remaining word-aligned tail as `trailingWords` instead of assigning unproven semantic names.
- The unresolved fallback diagnostic remains available for future `CharacterRootComponentData` variants that fail the inferred parser.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Rebuild result: 0 warnings, 0 errors.

Targeted validation output: `tmp\characterroot_decode_after_20260629`.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 30 |
| JSON parse failures | 0 |
| `CharacterRootComponentData` refs | 28 |
| Decoded `CharacterRootComponentData` refs | 28 |
| Remaining `$unparsed` refs in slice | 66 |

Observed decoded shape:

| Field/shape | Current evidence |
| --- | --- |
| locator IDs/names | 28/28 payloads, counts match exactly |
| `unknown0` | 27 payloads = `0`, Zhuangfy outlier = `1` |
| transform records | 27 payloads contain 6 records; Zhuangfy contains 0 in the first block |
| trailing words | preserved for every payload; 15 payloads have four zero words, several contain regular string-list-like blocks, Zhuangfy has a 308-word secondary/raw tail |

Remaining unresolved in the same validation slice after this pass:

| Class | Remaining `$unparsed` |
| --- | ---: |
| `Beyond.Gameplay.Core.Conditions.CheckObjectTypeMatch/Data` | 22 |
| `Beyond.Gameplay.Core.Conditions.CheckMainCharacterCondition/Data` | 7 |
| `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data` | 7 |
| `Beyond.Gameplay.Core.Conditions.CheckTargetsEqual/Data` | 6 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNum/Data` | 5 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag/Data` | 5 |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 |
| `Beyond.Gameplay.Core.Conditions.CheckTagMatch/Data` | 2 |
| `Beyond.Gameplay.Core.Conditions.CheckHp/Data` | 2 |
| `Beyond.Gameplay.Core.AbilitySystemData` | 2 |
| `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data` | 2 |
| `Beyond.Gameplay.Core.StoreBuffCount/Data` | 1 |

Current classification: `CharacterRootComponentData` is a normal serialized managed-reference payload, not missing VFS/AB bytes and not encryption. The main semantic gap is the exact meaning of `unknown0` and the tail list blocks, so the decoder is intentionally marked inferred and preserves raw tail words. The remaining blockers in this character slice are now the TargetSettings-based Core action/condition payloads plus `AbilitySystemData`.

## 2026-06-29 Thirty-Fifth Fresh StreamingAssets CheckHp And CheckTagMatch Batch

Follow-up after the CharacterRootComponentData batch. Work focused on the small remaining Core condition payloads that were not yet decoded in the current 30-file character validation slice: `Beyond.Gameplay.Core.Conditions.CheckHp/Data` and `Beyond.Gameplay.Core.Conditions.CheckTagMatch/Data`.

Evidence used:

- Current validation output `tmp\characterroot_decode_after_20260629` had two unresolved `CheckHp/Data` refs and two unresolved `CheckTagMatch/Data` refs, all in the 68B3 chunk.
- A read-only byte-layout audit confirmed the fallback hints covered the full payload word range for these four entries, but recommended adding full payload diagnostics before promotion.
- A narrow IL2CPP metadata query with `tools\endfield-il2cpp\catalog_option_flow_metadata.py --type-regex "CheckHp|CheckTagMatch" --include-all-members` confirmed:
  - `CheckHp/Data`: `hpOwner: TargetSettings`, `compare: Beyond.CompareType`, `isRatio: bool`, `value: BlackboardDouble`.
  - `CheckTagMatch/Data`: `checkTarget: TargetSettings`, `query: GameplayTagQuery`.
  - MemoryPack setter order matches those fields.
- A diagnostic-only pass first emitted `diagnosticFullPayloadHex`, `diagnosticRawWordTrace`, and `diagnosticStructuredLayout` for all four entries under `tmp\checkhp_checktag_trace_after_20260629`; all four remained `$unparsed` in that evidence pass.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added full diagnostic tracing for future unresolved `CheckHp/Data` and `CheckTagMatch/Data` fallback cases.
- Added structured diagnostics for both classes under the existing TargetSettings diagnostic path.
- Added guarded partial decoders for both classes:
  - inherited `AbilityActionData` prefix;
  - `hpOwner` / `checkTarget` via the existing partial `TargetSettings` diagnostic reader;
  - `CheckHp` `compare`, `isRatio`, and `BlackboardDouble value`;
  - `CheckTagMatch` `GameplayTagQuery` with bounded tag list.
- The decoded objects are explicitly marked `$partial` because `TargetSettings` selector-data and suffix semantics remain unresolved. This is not warning suppression: the payload is consumed completely, while unresolved sub-layout semantics stay visible inside the decoded object.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Final rebuild result: 0 warnings, 0 errors.

Targeted validation output: `tmp\checkhp_checktag_decode_after_20260629`.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 30 |
| JSON parse failures | 0 |
| `CheckHp/Data` refs | 2 |
| Decoded `CheckHp/Data` refs | 2 |
| `CheckTagMatch/Data` refs | 2 |
| Decoded `CheckTagMatch/Data` refs | 2 |
| Remaining `$unparsed` refs in slice | 62 |

Decoded sample facts:

| Class | Observed fields |
| --- | --- |
| `CheckHp/Data` | `hpOwner` partial TargetSettings length 108, `compare = LT`, `isRatio = true`, `value = 0.6` or `0.4`, empty blackboard key |
| `CheckTagMatch/Data` | partial TargetSettings length 100 or 108, query type `HasAny`, tag paths `Skill/Character/Common/SpellStatus/Conduct`, `Skill/Character/Common/SpellInflict/PulseInflict`, and `Skill/Character/Common/SpellStatus/Frozen` |

Remaining unresolved in the same validation slice after this pass:

| Class | Remaining `$unparsed` |
| --- | ---: |
| `Beyond.Gameplay.Core.Conditions.CheckObjectTypeMatch/Data` | 22 |
| `Beyond.Gameplay.Core.Conditions.CheckMainCharacterCondition/Data` | 7 |
| `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data` | 7 |
| `Beyond.Gameplay.Core.Conditions.CheckTargetsEqual/Data` | 6 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNum/Data` | 5 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag/Data` | 5 |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 |
| `Beyond.Gameplay.Core.AbilitySystemData` | 2 |
| `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data` | 2 |
| `Beyond.Gameplay.Core.StoreBuffCount/Data` | 1 |

Current classification: `CheckHp/Data` and `CheckTagMatch/Data` are normal serialized managed-reference payloads backed by local IL2CPP/MemoryPack metadata, not missing AB/VFS bytes and not encryption. They remain partial only because their TargetSettings subobject still contains unresolved selector/suffix semantics.

## 2026-06-29 Thirty-Sixth Fresh StreamingAssets TargetSettings-Only Condition Batch

Follow-up after the CheckHp/CheckTagMatch batch. Work focused on the TargetSettings-only parent condition payloads in the current 30-file character validation slice: `CheckMainCharacterCondition/Data`, `CheckObjectTypeMatch/Data`, and `CheckTargetsEqual/Data`.

Evidence used:

- The current validation output `tmp\checkhp_checktag_decode_after_20260629` still had 35 unresolved refs across these three classes: 22 `CheckObjectTypeMatch/Data`, 7 `CheckMainCharacterCondition/Data`, and 6 `CheckTargetsEqual/Data`.
- Existing fallback diagnostics already emitted full payload hex, raw word traces, and complete `diagnosticStructuredLayout` for these classes.
- A narrow IL2CPP metadata query with `tools\endfield-il2cpp\catalog_option_flow_metadata.py --type-regex "CheckObjectTypeMatch|CheckMainCharacterCondition|CheckTargetsEqual" --include-all-members` confirmed:
  - `CheckMainCharacterCondition/Data`: `checkTarget: TargetSettings`.
  - `CheckObjectTypeMatch/Data`: `target: TargetSettings`, `objectTypeMask: ObjectType`.
  - `CheckTargetsEqual/Data`: `firstTargetSettings: TargetSettings`, `secondTargetSettings: TargetSettings`.
  - MemoryPack setter order matches those fields.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added guarded partial decoders for all three classes.
- Each decoder consumes the inherited `AbilityActionData` prefix and the metadata-backed class-local fields completely.
- Each embedded TargetSettings object is still emitted via the existing partial TargetSettings diagnostic reader, preserving unresolved selector-data and suffix semantics instead of pretending those subfields are fully named.
- `CheckObjectTypeMatch/Data` now uses the metadata field name `target` for the TargetSettings object and preserves `objectTypeMask` as a raw hash-style int32 value.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Rebuild result: 0 errors and the same 14 existing warnings from AnimeStudio projects.

Targeted validation output: `tmp\target_simple_conditions_decode_after_20260629`.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 30 |
| JSON parse failures | 0 |
| `CheckObjectTypeMatch/Data` refs | 22 |
| Decoded `CheckObjectTypeMatch/Data` refs | 22 |
| `CheckMainCharacterCondition/Data` refs | 7 |
| Decoded `CheckMainCharacterCondition/Data` refs | 7 |
| `CheckTargetsEqual/Data` refs | 6 |
| Decoded `CheckTargetsEqual/Data` refs | 6 |
| Remaining `$unparsed` refs in slice | 27 |

Decoded sample facts:

| Class | Observed fields |
| --- | --- |
| `CheckObjectTypeMatch/Data` | partial TargetSettings length 100 or 108, `objectTypeMask = 0x10` in sampled entries |
| `CheckMainCharacterCondition/Data` | one partial TargetSettings object named `checkTarget` |
| `CheckTargetsEqual/Data` | two partial TargetSettings objects named `firstTargetSettings` and `secondTargetSettings`, length 100 or 108 in observed samples |

Remaining unresolved in the same validation slice after this pass:

| Class | Remaining `$unparsed` |
| --- | ---: |
| `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data` | 7 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNum/Data` | 5 |
| `Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag/Data` | 5 |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 |
| `Beyond.Gameplay.Core.AbilitySystemData` | 2 |
| `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data` | 2 |
| `Beyond.Gameplay.Core.StoreBuffCount/Data` | 1 |

Current classification: these 35 condition payloads are normal serialized managed-reference payloads backed by local IL2CPP/MemoryPack metadata, not missing AB/VFS bytes and not encryption. They remain `$partial` only because their embedded TargetSettings objects still preserve unresolved selector/suffix fields.

## 2026-06-29 Thirty-Seventh Fresh StreamingAssets Buff-Stack Condition Batch

Follow-up after the simple TargetSettings-only condition batch. Work focused on the remaining regular buff-stack condition payloads in the current character validation slice: `Beyond.Gameplay.Core.Conditions.CheckBuffStackNum/Data` and `Beyond.Gameplay.Core.Conditions.CheckBuffStackNumByTag/Data`.

Evidence used:

- The latest focused validation output before this pass still had 10 raw `$unparsed` refs across these two classes: 5 `CheckBuffStackNum/Data` and 5 `CheckBuffStackNumByTag/Data`.
- Local IL2CPP metadata from `global-metadata.dat` names the inherited `AbilityActionData` prefix and direct fields:
  - `CheckBuffStackNum/Data`: `checkTarget: TargetSettings`, `buffId: BuffId`, `compareType: Beyond.CompareType`, `value: BlackboardDouble`.
  - `CheckBuffStackNumByTag/Data`: `checkTarget: TargetSettings`, `tagQuery: GameplayTagQuery`, `buffStackNumType: BuffStackNumType`, `compareType: Beyond.CompareType`, `value: BlackboardDouble`.
- Metadata and subagent review confirmed MemoryPack setter method order is not byte order for these classes; the defensible byte order is IL2CPP field order plus observed complete payload consumption.
- Existing structured diagnostics already consumed both classes to `reader.EnsureComplete()` and showed stable values: `buff_physical_no_guard` for regular checks, GameplayTagQuery entries for by-tag checks, `compareType = GE`, and BlackboardDouble values with empty blackboard keys.
- A parallel raw-layout subagent audit found `CheckBuffStackNumAdvanced/Data` still lacks a Core-namespace structured diagnostic in the current validation output; it has plausible `BuffFindSettings` shapes, but should not be semantically decoded until that union/list layout is traced directly.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Promoted `CheckBuffStackNum/Data` from diagnostic-only to a guarded partial decoder.
- Promoted `CheckBuffStackNumByTag/Data` from diagnostic-only to a guarded partial decoder.
- Both decoders consume the inherited `AbilityActionData` prefix and every metadata-backed direct field.
- Both keep embedded `TargetSettings` as `$partial`, preserving unresolved selector/suffix fields instead of assigning unproven names.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Rebuild result: 0 errors and the same 14 existing warnings from AnimeStudio projects.

Targeted validation output: `tmp\buff_stack_conditions_decode_after_20260629` from the same three character chunks used by the prior condition batches.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 28 |
| JSON parse failures | 0 |
| `CheckBuffStackNum/Data` refs | 5 |
| Decoded `CheckBuffStackNum/Data` refs | 5 |
| Remaining `$unparsed` `CheckBuffStackNum/Data` refs | 0 |
| `CheckBuffStackNumByTag/Data` refs | 5 |
| Decoded `CheckBuffStackNumByTag/Data` refs | 5 |
| Remaining `$unparsed` `CheckBuffStackNumByTag/Data` refs | 0 |

Decoded sample facts:

| Class | Observed fields |
| --- | --- |
| `CheckBuffStackNum/Data` | `checkTarget` partial TargetSettings, `buffId = buff_physical_no_guard`, `compareType = GE`, BlackboardDouble values including 1.0, 3.0, and 4.0 |
| `CheckBuffStackNumByTag/Data` | `checkTarget` partial TargetSettings, GameplayTagQuery entries for `VulnerablePhysic`, `FractureStatus`, `CrystInflict`, `NaturalInflict`, and `SpellInflict`, `buffStackNumType = 0`, `compareType = GE`, BlackboardDouble values including 1.0 and 2.0 |

Remaining raw `$unparsed` refs in the same validation slice after this pass:

| Class | Remaining `$unparsed` |
| --- | ---: |
| `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data` | 7 |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 |
| `Beyond.Gameplay.Core.AbilitySystemData` | 2 |
| `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data` | 2 |
| `Beyond.Gameplay.Core.StoreBuffCount/Data` | 1 |

Current classification: these 10 regular/by-tag buff-stack condition payloads are normal serialized managed-reference payloads backed by local IL2CPP metadata, not missing VFS/AB bytes and not encryption. They remain `$partial` only because their embedded TargetSettings objects still preserve unresolved selector/suffix fields. `CheckBuffStackNumAdvanced/Data` remains intentionally unresolved until its `BuffFindSettings` variants are traced under the actual `Beyond.Gameplay.Core` namespace and byte-proven.

## 2026-06-29 Thirty-Eighth Fresh StreamingAssets Action Blackboard Batch

Follow-up after the regular buff-stack condition batch. Work focused on the safest remaining Core action payloads in the current character validation slice: `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data` and `Beyond.Gameplay.Core.StoreBuffCount/Data`.

Evidence used:

- The latest focused validation output before this pass still had 2 raw `$unparsed` `ModifyDynamicBlackboard/Data` refs, both 164 bytes, and 1 raw `$unparsed` `StoreBuffCount/Data` ref at 184 bytes.
- Local IL2CPP metadata names the direct fields after inherited `AbilityActionData`:
  - `ModifyDynamicBlackboard/Data`: `key`, `operation`, `directValue`, `value`, `calculationTarget`, and `calculateType`.
  - `StoreBuffCount/Data`: `useCurrentBuff`, `buffOwners`, `buffId`, and `blackboardKey`.
- Existing structured diagnostics already consumed all three payloads to `reader.EnsureComplete()` with the same byte order.
- A parallel verification subagent independently confirmed both classes are safe guarded partial-decoder candidates. `StoreBuffCount/Data` has only one observed sample, but its field order, bounded strings, bool32 value, TargetSettings boundary, and complete payload consumption are byte-proven.
- A separate Advanced buff-stack subagent confirmed `CheckBuffStackNumAdvanced/Data` should stay diagnostic-only for now: it is under `Beyond.Gameplay.Core`, while the current full-trace predicate only whitelists the Advanced class under `Beyond.Gameplay.Core.Conditions`, and its `BuffFindSettings` variants still need direct tracing.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Added a guarded partial decoder for `Beyond.Gameplay.Core.ModifyDynamicBlackboard/Data`.
- Added a guarded partial decoder for `Beyond.Gameplay.Core.StoreBuffCount/Data`.
- Both decoders consume the inherited `AbilityActionData` prefix and every metadata-backed direct field.
- Embedded `calculationTarget` and `buffOwners` remain partial TargetSettings diagnostic objects because selector-data RID slots and suffix word semantics are still not fully named.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Final rebuild result after both decoder branches: 0 warnings and 0 errors.

Targeted validation output: `tmp\action_blackboard_decode_after_20260629` from the same three character chunks used by the prior condition batches.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 28 |
| JSON parse failures | 0 |
| `ModifyDynamicBlackboard/Data` refs | 2 |
| Decoded `ModifyDynamicBlackboard/Data` refs | 2 |
| Remaining `$unparsed` `ModifyDynamicBlackboard/Data` refs | 0 |
| `StoreBuffCount/Data` refs | 1 |
| Decoded `StoreBuffCount/Data` refs | 1 |
| Remaining `$unparsed` `StoreBuffCount/Data` refs | 0 |

Decoded sample facts:

| Class | Observed fields |
| --- | --- |
| `ModifyDynamicBlackboard/Data` | `key = EntityBB_combo_type`, `operation = Assign`, `directValue = true`, BlackboardDouble values `0.0` and `1.0`, partial 100-byte `calculationTarget`, `calculateType = HpRatio` |
| `StoreBuffCount/Data` | `useCurrentBuff = false`, partial 108-byte `buffOwners`, `buffId = buff_physical_no_guard`, `blackboardKey = EntityBB_noguard_count` |

Remaining raw `$unparsed` refs in the same validation slice after this pass:

| Class | Remaining `$unparsed` |
| --- | ---: |
| `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data` | 7 |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 |
| `Beyond.Gameplay.Core.AbilitySystemData` | 2 |

Current classification: these 3 action/blackboard payloads are normal serialized managed-reference action payloads backed by local IL2CPP metadata, not missing VFS/AB bytes and not encryption. They remain `$partial` only because their embedded TargetSettings objects still preserve unresolved selector/suffix fields. The next useful non-decoding improvement is a diagnostic-only Core-namespace full trace for `CheckBuffStackNumAdvanced/Data` so its `BuffFindSettings` variants can be byte-proven before semantic promotion.

## 2026-06-29 Thirty-Ninth Fresh StreamingAssets Advanced Buff-Stack Diagnostic Batch

Follow-up after the action blackboard batch. Work focused on `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data`, but intentionally as diagnostics only. The goal was to expose full payload evidence for the unresolved `BuffFindSettings` sublayout without converting the parent managed reference into a decoded success path.

Evidence used:

- The current focused validation slice still has 7 raw `$unparsed` `CheckBuffStackNumAdvanced/Data` refs with lengths 200, 240, and 252 bytes.
- A subagent audit confirmed the previous full-trace whitelist was wrong for this class: it listed `CheckBuffStackNumAdvanced/Data` under `Beyond.Gameplay.Core.Conditions`, but the actual managed-reference namespace is `Beyond.Gameplay.Core`.
- Local IL2CPP metadata names direct fields as `checkTarget`, `buffSettings`, `buffStackNumType`, `compareType`, `value`, and `limitSkillCastId`.
- A separate byte-layout audit over all 7 payloads identified two observed `BuffFindSettings` candidate shapes:
  - `checkType = Id`: bounded buff-id string list followed by an empty GameplayTagQuery.
  - `checkType = Tag`: optional buff-id string list followed by a bounded GameplayTagQuery with one or two tag records.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Moved the full-payload trace whitelist for `CheckBuffStackNumAdvanced/Data` to the real `Beyond.Gameplay.Core` namespace.
- Removed the stale `Beyond.Gameplay.Core.Conditions` whitelist entry for the Advanced class.
- Added a diagnostic-only structured branch for `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data`.
- Added `ReadDiagnosticBuffFindSettingsCandidate`, which emits a bounded candidate layout for `checkType`, `buffIdList`, and `tagQuery` while marking it `$partial`.
- Did not add a `TryDecodeCoreActionConditionManagedReferenceData` success branch. The parent payload remains `$unparsed` by design.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Rebuild result: 0 errors and the same 14 existing warnings from AnimeStudio projects.

Targeted validation output: `tmp\advanced_buff_trace_after_20260629` from the same three character chunks used by the prior condition/action batches.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 28 |
| JSON parse failures | 0 |
| `CheckBuffStackNumAdvanced/Data` refs | 7 |
| Refs still intentionally `$unparsed` | 7 |
| Refs with `diagnosticFullPayloadHex` | 7 |
| Refs with `diagnosticRawWordTrace` | 7 |
| Refs with `diagnosticStructuredLayout` | 7 |

Observed Advanced candidate variants:

| Shape | Count | Observed data |
| --- | ---: | --- |
| `checkType = Id`, one buff id, empty tag query | 2 | `buff_chr_0023_antal_tageffect`, `compareType = GE`, value `1.0` |
| `checkType = Id`, two buff ids, empty tag query | 2 | `buff_chr_0028_wulfa_combo_usetimer`, `buff_chr_0028_wulfa_combo_cannottrigger`, `compareType = LT`, value `1.0` |
| `checkType = Tag`, no buff ids, two tags | 1 | `Skill/Character/Common/NoGuard`, `Skill/Character/Common/SpellInflict`, `compareType = Equals`, value `0.0` |
| `checkType = Tag`, one buff id, one tag | 2 | `buff_chr_0030_zhuangfy_have_sword`, `Skill/Character/Common/SpellInflict/PulseInflict`, `compareType = GE`, value `1.0` |

Remaining raw `$unparsed` refs in the same validation slice after this pass:

| Class | Remaining `$unparsed` |
| --- | ---: |
| `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data` | 7 |
| `Beyond.Gameplay.Core.CreateBuffAction/Data` | 5 |
| `Beyond.Gameplay.Core.AbilitySystemData` | 2 |

Current classification: the Advanced buff-stack payload bytes are now fully preserved and structurally inspectable, but the class is not considered semantically decoded yet. The new evidence strongly suggests a `BuffFindSettings` shape of `checkType + buff-id list + GameplayTagQuery`, followed by `buffStackNumType`, `compareType`, BlackboardDouble `value`, and `limitSkillCastId`, but the parent remains `$unparsed` until broader samples prove every `BuffFindSettings.CheckType` variant and the generic/list contract.

## 2026-06-30 Fortieth Fresh StreamingAssets Advanced Buff-Stack Partial Decode Validation

Follow-up after the diagnostic-only Advanced buff-stack batch. The current AnimeStudio exporter now has a guarded `TryDecodeCoreActionConditionManagedReferenceData` branch for `Beyond.Gameplay.Core.CheckBuffStackNumAdvanced/Data`, so this pass validated that branch against the same focused character slice instead of adding new parser code.

Evidence used:

- The prior diagnostic trace byte-proved all 7 observed Advanced payloads with lengths 200, 240, and 252 bytes.
- Local IL2CPP metadata names the direct field order as `checkTarget`, `buffSettings`, `buffStackNumType`, `compareType`, `value`, and `limitSkillCastId`.
- Guide-focused parallel subagents found no current guide `$unparsed` target in `tmp\current_cli_probe_topfamilies_20260630\guide`; guide is verification-only for now, so the unresolved non-guide Advanced buff-stack class stayed the active target.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Rebuild result: 0 errors and the same 14 existing warnings from AnimeStudio projects.

Targeted validation output: `tmp\advanced_buff_decode_after_20260630_try2` from the three current installed-game VFS chunks:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk
```

The old `71FC2E714440BA2EC25896BA8E09F866.chk` and `FBAD673F42623B59F1A82C68E760FB0B.chk` paths were stale for the current install; the current files were located by prefix before rerunning those two chunks.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 30 |
| JSON parse failures | 0 |
| Decoded `CheckBuffStackNumAdvanced/Data` data records | 7 |
| Advanced records marked `$partial` | 7 |
| Advanced records still `$unparsed` | 0 |
| Advanced records marked `$heuristic` | 0 |
| Advanced records with `decodeError` | 0 |
| Overall `$unparsed` records in this validation slice | 0 |

Observed Advanced decoded variants:

| Shape | Count | Observed data |
| --- | ---: | --- |
| `checkType = Id`, one buff id, empty tag query | 2 | `buff_chr_0023_antal_tageffect`, `compareType = GE`, value `1.0`, `limitSkillCastId = false` |
| `checkType = Id`, two buff ids, empty tag query | 2 | `buff_chr_0028_wulfa_combo_usetimer`, `buff_chr_0028_wulfa_combo_cannottrigger`, `compareType = LT`, value `1.0`, `limitSkillCastId = false` |
| `checkType = Tag`, no buff ids, two tags | 1 | `Skill/Character/Common/NoGuard`, `Skill/Character/Common/SpellInflict`, `compareType = Equals`, value `0.0`, `limitSkillCastId = false` |
| `checkType = Tag`, one buff id, one tag | 2 | `buff_chr_0030_zhuangfy_have_sword`, `Skill/Character/Common/SpellInflict/PulseInflict`, `compareType = GE`, value `1.0`, `limitSkillCastId = false` |

Residual diagnostics:

- The validation slice still has object-level `managedReferencesRegistryRecovery` heuristic/decode-error notes on 28 character files. These are recovery diagnostics from the original TypeTree registry reader losing sync before the managed-reference recovery pass, not failed Advanced payload decodes.
- `AbilitySystemData`, `SkillDataBundle`, `TargetSettings`, and `SelectorData` remain `$partial` where expected because selector suffix/post-processor semantics are still not fully named.

Current classification: `CheckBuffStackNumAdvanced/Data` is no longer a raw `$unparsed` managed-reference payload in the focused validation slice. It is now byte-consumed and exported as a decoded `$partial` record with named direct fields. It is still not fully semantic because embedded `TargetSettings` and `BuffFindSettings` keep partial notes until unobserved selector/post-processor and `Environment`/`Context` `BuffFindSettings.CheckType` variants are proven.

## 2026-06-30 Forty-First Fresh StreamingAssets Managed-Reference Registry Status Clarification

Follow-up after the Advanced buff-stack partial decode validation. Work focused on the object-level `managedReferencesRegistryRecovery` diagnostics that still appeared scary in focused character outputs even when all recovered managed-reference payloads were decoded or partial-decoded.

Evidence used:

- A parallel registry-recovery subagent inspected `tmp\advanced_buff_decode_after_20260630_try2`, `Exporter.cs`, `TypeTreeHelper.cs`, `EndianBinaryReader.cs`, `ObjectReader.cs`, and `MonoBehaviour.cs`.
- The subagent found the registry headers/counts are recovered correctly. The large `ReadAlignedString` lengths are serialized TypeTree fallback failures after Unity's TypeTree reaches `ReferencedObjectData` without a payload schema and begins reading managed-reference payload bytes as if they were registry header strings.
- Example: `808661040 = 0x30333030`, bytes `30 30 33 30`, ASCII `0030` from `chr_0030_zhuangfy`; this is payload text misread as a string length, not an encrypted or missing registry block.
- `expectedRidCount` in the old metadata was misleading: it was collected from the pre-registry partial TypeTree payload, often just `data.rid = 1`, not the actual registry entry count.

Implemented in `tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`:

- Split recovered registry status into `fullyDecoded`, `partialDecoded`, and `heuristic`.
- A recovered registry with only `$partial` child payloads now reports `status = partialDecoded` and sets `references.$partial`, not `status = heuristic` and `references.$heuristic`.
- Real weak-header, `$unparsed`, or `$heuristic` child payloads still keep `status = heuristic`.
- Added `preRegistryRidCount` while keeping the old `expectedRidCount` for compatibility.
- Added actual `registryCount`, `recoveredRidCount`, `registryStartOffset`, and `typeTreeFailureOffset` fields when available.
- Moved the TypeTree fallback exception to `typeTreeDecodeError` for `partialDecoded` cases. `decodeError` remains reserved for genuinely heuristic recovered registries.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Rebuild result: 0 warnings, 0 errors.

Targeted validation output: `tmp\registry_status_after_20260630` from the same three current installed-game VFS chunks used by the Advanced buff-stack validation.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 30 |
| Registry recovery metadata blocks | 30 |
| `partialDecoded` registries | 28 |
| `fullyDecoded` registries | 2 |
| `heuristic` registries | 0 |
| Registry count mismatches | 0 |
| Data-level `$unparsed` records | 0 |
| Data-level `$heuristic` records | 0 |
| Data-level `decodeError` records | 0 |

Representative generated metadata after the change:

```json
{
  "field": "references",
  "type": "ManagedReferencesRegistry",
  "status": "partialDecoded",
  "preRegistryRidCount": 1,
  "expectedRidCount": 1,
  "typeTreeDecodeError": "EndOfStreamException: ReadAlignedString requests 808661040 bytes at offset 0x11C24, but only 10964 bytes remain.",
  "registryStartOffset": 64,
  "typeTreeFailureOffset": 180,
  "registryCount": 43,
  "recoveredRidCount": 43
}
```

Current classification: these focused character registry diagnostics are not evidence of missing VFS bytes, encryption, or an unresolved managed-reference registry format. They are evidence that the serialized TypeTree path cannot decode arbitrary managed-reference payload schemas directly, after which AnimeStudio's recovery pass locates the registry and decodes payloads with local per-class parsers. Remaining work is semantic payload recovery, especially `AbilitySystemData`, `SkillDataBundle`, `TargetSettings`, `SelectorData`, and unobserved selector/post-processor variants.
