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
