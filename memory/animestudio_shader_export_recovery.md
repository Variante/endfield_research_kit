# AnimeStudio Shader Export Recovery

Date: 2026-06-28
Scope: Shader parsing/export only.

## Inputs inspected

- Required workflow notes: `.codex/skills/animestudio-workflow/SKILL.md`, `.codex/skills/animestudio-workflow/references/animestudio.md`.
- Prior context: `memory/animestudio_ab_understanding_report.md`.
- Failure logs: `reports/20260627_215637/*/*Shader*.stdout.log`.
- Asset maps: `export_full/recovered/AnimeStudio-cli/*/maps/*.json`.

## Findings

The 20260627_215637 Shader conversion failures are converter failures, not Shader object-reader failures. The failing stack reaches `AnimeStudio.Utility/ShaderConverter.cs`, after the Endfield `Shader` object has already parsed.

Failure count in the existing logs: 454 `Export Shader` errors. The dominant exception is `ReadAlignedString` with huge string lengths while reading `ShaderSubProgram` records.

Representative decoded bogus string lengths:

| Decimal | Hex | Little-endian text | Meaning |
| ---: | --- | --- | --- |
| 1953066581 | 0x74696E55 | `Unit` | parser landed in shader text/header bytes |
| 1684105299 | 0x64616853 | `Shad` | parser landed in shader text/header bytes |
| 1869367135 | 0x6F6C475F | `_Glo` | parser landed in shader code/identifier bytes |
| 1381257823 | 0x5254525F | `_RTR` | parser landed in shader code/identifier bytes |

For Endfield live-game shaders, `Shader.cs` reads `subShaderBlobs` and `m_CompressionType`, then `ShaderConverter.Convert` prefers `subShaderBlobs`. LZ4 decompression succeeds in the sampled failures, but the decompressed segment is not the legacy Unity serialized `ShaderSubProgram` layout expected by the converter. The evidence points to a newer Unity/Endfield player shader blob variant, or an already transformed/encrypted bytecode payload, where program metadata and raw bytecode are no longer shaped like the converter expects.

## Patch

Changed `tools/AnimeStudio/AnimeStudio.Utility/ShaderConverter.cs` only.

Behavior after the patch:

- Full shader conversion still runs first.
- Recoverable shader blob decode failures are caught inside shader conversion, not in the broad exporter error path.
- The exporter writes a `.shader` file with parsed Shader metadata and an explicit bytecode-unavailable classification comment.
- The CLI logs a warning such as:
  `Shader HGRP/UI/Grid exported without bytecode: unsupported shader bytecode blob layout ...`
- Missing parsed subprograms are handled as unavailable bytecode comments instead of null/index errors.

This does not claim to decompile the unsupported Endfield shader bytecode. It prevents known unsupported blob variants from appearing as `Export Shader error` and preserves the useful parsed metadata for indexing/review.

## Minimal reproduction and verification

Before patch, this one-row filter reproduced the report failure:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\animestudio_shader_repro_before --game ArknightsEndfield --logger_flags Info Warning Error --group_assets ByType --export_type Convert --types Shader:Both --filter_data tmp\animestudio_shader_mobile_particles_filter.json
```

Result before patch: `Export Shader:Mobile/Particles/Additive error`, `ReadAlignedString requests 1953066581 bytes at offset 0x3C`, no asset exported.

Build after patch:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded, 0 warnings, 0 errors.

Targeted verifications after patch:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\animestudio_shader_repro_after --game ArknightsEndfield --logger_flags Info Warning Error --group_assets ByType --export_type Convert --types Shader:Both --filter_data tmp\animestudio_shader_mobile_particles_filter.json
```

Result: exported 1 asset, warning-classified `Unit` signature, no `Export Shader` error.

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk" tmp\animestudio_shader_repro_streaming_raytracing --game ArknightsEndfield --logger_flags Info Warning Error --group_assets ByType --export_type Convert --types Shader:Both --filter_data tmp\animestudio_shader_streaming_raytracing_filter.json
```

Result: exported 1 asset, warning-classified `_RTR` signature, no `Export Shader` error.

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\0CE8FA57\FCF21734CEDE10386D06530C787F510D.chk" tmp\animestudio_shader_repro_persistent_grid --game ArknightsEndfield --logger_flags Info Warning Error --group_assets ByType --export_type Convert --types Shader:Both --filter_data tmp\animestudio_shader_persistent_grid_filter.json
```

Result: exported 1 asset, warning-classified `_Glo` signature, no `Export Shader` error.

## Remaining risks

- The patch classifies unsupported shader bytecode variants but does not reverse the newer Endfield/Unity shader blob layout.
- Broad Shader conversion was not rerun across all 493 Shader map entries in this slice; the sampled failures cover both source roots and several dominant signatures from the report.
- Future conversion failures outside recoverable blob parsing, for example native decompiler failures after a parsed subprogram is available, may still surface separately.
