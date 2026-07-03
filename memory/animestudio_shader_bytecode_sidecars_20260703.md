# AnimeStudio shader bytecode sidecar recovery

Date: 2026-07-03

## Result

AnimeStudio now has an opt-in shader bytecode sidecar path for Endfield shader
recovery. Set `ANIMESTUDIO_EXPORT_SHADER_BYTECODE_SIDECARS=1` when running the
CLI to write raw shader bytecode beside converted `.shader` exports:

```text
<exported shader>.shader.bytecode/
  0000_endfield_dxbc_0.dxbc
  0001_endfield_dxbc_1.dxbc
  0002_endfield_smolv_0.smolv
  0003_endfield_spirv_0.spv
  ...
```

The default export path is unchanged: when the env var is absent, shader export
does not write sidecar comments or sidecar files. The exporter also clears the
matching `.shader.bytecode` directory before each shader export, so old sidecar
files do not survive when a later export has fewer snippets or sidecars are
disabled.

## Implementation

Changed files in `tools/AnimeStudio`:

- `AnimeStudio.CLI/Exporter.cs`
  - derives the sidecar root as `<exportFullPath>.bytecode`;
  - enables it only for `ANIMESTUDIO_EXPORT_SHADER_BYTECODE_SIDECARS=1/true/yes`;
  - deletes any stale sidecar directory for the shader output before conversion.
- `AnimeStudio.Utility/ShaderConverter.cs`
  - adds a per-export shader context with bytecode sidecar support;
  - writes Endfield D3D11 snippets as `.dxbc`;
  - writes Endfield Vulkan snippets as raw `.smolv`;
  - when sidecars are enabled, decodes SMOL-V snippets and writes decoded
    `.spv` files;
  - leaves sidecar writes best-effort and records a shader comment if a sidecar
    write fails.

The `.spv` decode is guarded by the active sidecar root, so the default path
does not do sidecar-only SMOL-V decode work.

## Validation

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded with 12 existing TODO/unused-variable warnings in
unrelated AnimeStudio utility files and 0 errors.

Targeted export:

```bat
set ANIMESTUDIO_EXPORT_SHADER_BYTECODE_SIDECARS=1
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" ^
  tmp\shader_sidecar_probe_20260703 ^
  --game ArknightsEndfield ^
  --logger_flags Info Warning Error ^
  --group_assets ByType ^
  --export_type Convert ^
  --types Shader:Both ^
  --filter_data tmp\animestudio_shader_mobile_particles_filter.json
```

Sample: `Mobile/Particles/Additive`

Sidecars emitted:

```text
0000_endfield_dxbc_0.dxbc    784 bytes
0001_endfield_dxbc_1.dxbc    376 bytes
0002_endfield_smolv_0.smolv  874 bytes
0003_endfield_spirv_0.spv   3868 bytes
0004_endfield_smolv_1.smolv  209 bytes
0005_endfield_spirv_1.spv    652 bytes
```

The `.shader` text includes `AnimeStudio bytecode sidecar` comments immediately
after the corresponding Endfield DXBC/SMOL-V snippet comments.

Default-path and stale-cleanup check:

- sidecar-enabled export to `tmp\shader_sidecar_stale_check_20260703` emitted
  6 sidecar files;
- rerunning the same export path with the env var unset left 0 sidecar files
  and 0 `.bytecode` directories;
- no `AnimeStudio bytecode sidecar` comments remained in the default `.shader`
  output.

Ruri proof:

```bat
.\tools\Ruri.ShaderDecompiler\bin-flat\Release\net8.0\Ruri.ShaderDecompiler.exe ^
  tmp\shader_sidecar_probe_20260703\Shader\Mobile_Particles_Additive_p27A1E9100F440F4C.shader.bytecode\0000_endfield_dxbc_0.dxbc ^
  - ^
  > tmp\shader_sidecar_probe_20260703\ruri_0000_endfield_dxbc_0.hlsl
```

Result: exit code 0 and a 4800-byte HLSL output. The output starts with named
constant-buffer slots such as `CB0UBO`, `CB1UBO`, and `CB2UBO`, plus recovered
vertex input/output structs.

## Toolchain implications

This sidecar path gives downstream shader tools stable raw inputs:

- Ruri.ShaderDecompiler can consume isolated DXBC sidecars now, and its Unity
  path is designed around bytecode plus engine metadata.
- `spirv-cross` can work from the decoded `.spv` sidecars for readable GLSL,
  HLSL, MSL, or reflection checks.
- HLSLcc-style DXBC translators can consume the `.dxbc` sidecars directly.
- AssetStudio/AssetRipper-style Unity extractors remain useful comparison
  tools, but AnimeStudio is now the narrow Endfield-aware bridge from VFS shader
  records to raw bytecode artifacts.

Online sources checked:

- https://github.com/ShiyumeMeguri/Ruri.ShaderDecompiler
- https://github.com/aras-p/smol-v
- https://vulkan.lunarg.com/doc/view/1.3.290.0/windows/spirv_toolchain.html
- https://github.com/Unity-Technologies/HLSLcc
- https://github.com/Perfare/AssetStudio
- https://github.com/AssetRipper/AssetRipper
- https://github.com/Perfare/Il2CppDumper
- https://github.com/SamboyCoding/Cpp2IL
- https://github.com/djkaty/Il2CppInspector

## Next useful experiments

1. Add a tiny helper or graph import that summarizes shader sidecar counts by
   shader name, platform, and extension, without putting sidecar output in the
   normal WebUI build.
2. Generate metadata JSON for the Ruri Unity path from AnimeStudio shader
   binding/resource records and test whether Ruri can recover material/resource
   names beyond generic constant-buffer slots.
3. Run the same sidecar export over the known `HGRP/UI/Grid` sample because it
   previously produced 144 DXBC and 144 SMOL-V snippets, making it a stronger
   stress test for stale cleanup and sidecar naming.
