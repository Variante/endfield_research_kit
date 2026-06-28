# AnimeStudio AnimationClip Recovery

Generated from the `reports/20260627_215637` AnimationClip conversion logs and targeted replays on 2026-06-28.

## Scope

This pass covered AnimeStudio `AnimationClip` parsing/export only. It did not change Shader, MonoBehaviour, wrapper scripts, or broad WebUI export behavior.

## Existing Failure Evidence

The report logs under `reports/20260627_215637/*/*AnimationClip*.stdout.log` showed per-asset conversion exceptions, not process-level crashes.

Observed signatures:

- `Unknown attribute 44543834 for Light`
- `Unknown attribute 1127824095 for Light`
- unknown custom binding type `39`

All stack traces reached `AnimeStudio.Utility/YAML/CustomCurveResolver.cs` through `AnimationClipConverter.AddCustomCurve`. The parser had already loaded these assets far enough to reach YAML conversion; the reproduced failures were unsupported custom curve binding names, not malformed object counts or ACL decompression failures.

The previous report counted:

- `StreamingAssets` AnimationClip: 117,849 matched, 117,782 outputs, 67 missing, 42 export errors.
- `Persistent` AnimationClip: 7,984 matched, 7,976 outputs, 8 missing, 8 export errors.

## Minimal Reproduction

Created temporary repro filters:

- `tmp/animestudio_animationclip_repro_filter_data.json`
- `tmp/animestudio_animationclip_repro_names.txt`

The four-row repro covers:

- Light attribute `44543834`
- Light attribute `1127824095`
- custom binding type `39`

Before the fix, the current CLI reproduced four `Export AnimationClip ... error` lines and produced no `.anim` files for the selected rows.

## Fix

`AnimeStudio.Utility/YAML/CustomCurveResolver.cs` now falls back to stable placeholder names for unresolved custom curve attributes instead of throwing:

- known custom type with unknown attribute: `unknown_<Type>_<attribute>`
- unknown custom type: `unknown_CustomType<byte>_<attribute>`

Examples from verified output:

- `unknown_Light_44543834`
- `unknown_Light_1127824095`
- `unknown_CustomType39_1865675821`

This preserves the curve data in exported YAML and classifies the unsupported binding explicitly, instead of dropping the entire AnimationClip export.

## Verification

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded. Existing TODO/compiler warnings remained; no errors.

Four-row targeted replay:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" "D:\fluffy-dump\tmp\animestudio_animationclip_repro_after" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type Convert --dummy_dlls "D:\fluffy-dump\tools\DummyDll" --names "D:\fluffy-dump\tmp\animestudio_animationclip_repro_names.txt" --filter_data "D:\fluffy-dump\tmp\animestudio_animationclip_repro_filter_data.json" --types AnimationClip:Both
```

Result: no warning/error output; 4 `.anim` files produced.

StreamingAssets shard 04 replay:

- prior report shard error count: 12 `Export AnimationClip` errors
- after fix: no warning/error output
- requested: 15,643
- produced: 15,643
- missing: 0

Persistent shard 01 replay:

- prior report shard error count: 8 `Export AnimationClip` errors
- after fix: no warning/error output
- requested: 7,922
- produced: 7,922
- missing: 0

## Remaining Risks

- Placeholder attributes preserve data but do not identify the original Unity property name. If those fields become important for downstream import fidelity, map the CRCs/custom type to concrete Unity/Endfield property names later.
- Full all-shard AnimationClip replay was not run in this pass. The verified shards cover all observed failure classes in the report, but untested shards could still contain unrelated AnimationClip converter issues.
- Existing local submodule changes in `AnimeStudio.CLI/Exporter.cs`, `AnimeStudio.CLI/Studio.cs`, and `AnimeStudio.Utility/ShaderConverter.cs` were not authored by this pass and were preserved.
