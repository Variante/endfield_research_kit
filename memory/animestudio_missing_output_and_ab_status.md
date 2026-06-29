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
