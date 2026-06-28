# AnimeStudio Export Recovery Progress - 2026-06-28

This is the first integrated progress checkpoint after splitting recovery work
by failure class.

## Completed Tracks

### Shader

- Owner: shader worker.
- File changed: `tools/AnimeStudio/AnimeStudio.Utility/ShaderConverter.cs`.
- Previous failure: shader bytecode decode exceptions surfaced as `Export Shader`
  errors and dropped the `.shader` output.
- Current behavior: recoverable shader bytecode blob failures export parsed
  shader metadata plus explicit bytecode-unavailable comments.
- Verification:
  - targeted `Mobile/Particles/Additive` repro now exports 1 `.shader` with a
    classified `Unit` signature warning.
  - targeted `Hidden/RayTracingReflection` repro exports 1 `.shader` with a
    classified `_RTR` signature warning.
  - targeted Persistent `HGRP/UI/Grid` repro exports 1 `.shader` with a
    classified `_Glo` signature warning.

Remaining unknown: the newer Endfield/Unity shader bytecode payload is still
not decompiled. We now preserve metadata and classify the blob instead of
pretending the bytecode is understood.

### AnimationClip

- Owner: AnimationClip worker.
- File changed:
  `tools/AnimeStudio/AnimeStudio.Utility/YAML/CustomCurveResolver.cs`.
- Previous failure: unknown custom curve binding attributes threw exceptions
  and dropped whole `.anim` files.
- Current behavior: unknown custom bindings export as stable placeholder field
  names such as `unknown_Light_44543834` and
  `unknown_CustomType39_1865675821`.
- Verification:
  - four-row targeted repro now exports 4 `.anim` files with no warning/error
    output.
  - StreamingAssets shard 04 replay requested 15,643 clips and produced 15,643.
  - Persistent shard 01 replay requested 7,922 clips and produced 7,922.

Remaining unknown: placeholder names preserve data but do not identify the
original Unity or Endfield property names.

## Shared Diagnostics

- File changed: `tools/AnimeStudio/AnimeStudio.CLI/Studio.cs`.
- Top-level export catch logs now include PathID, source file, original source
  path, and container. This is intended to make the next full report map export
  warnings/errors back to source AB/VFS evidence.

## Verification

The combined current AnimeStudio source, including still-uncommitted parallel
worker changes, compiled successfully to a temporary output directory:

```bat
.\tools\AnimeStudio\.dotnet\dotnet.exe build .\tools\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release -f net9.0-windows --no-restore -p:OutDir=D:\fluffy-dump\tmp\animestudio_build_check\
```

Result: build succeeded with the existing TODO/compiler warnings only and 0
errors.

The normal release output was temporarily locked by active worker repro runs, so
the temp output build was used for this checkpoint.

## Active Tracks

- MonoBehaviour worker: still investigating partial managed-reference/type-tree
  recovery and source-context warnings.
- Missing-output/status worker: still investigating Texture2D/Sprite accounting
  and per-AB status reporting.

Files from active tracks are intentionally left unstaged until their workers
return final verification.
