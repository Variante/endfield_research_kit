# Animator No-Mesh Dependency Recovery - 2026-06-30

## Scope

Focused recovery pass for the stored AnimeStudio warning family:

```text
[Warning] Animator no output reason=no_mesh ...
```

The checked available logs contain 57,025 such warnings, all from:

```text
reports/20260628_194720/StreamingAssets/StreamingAssets_animestudio_convert_by_type.stdout.log
```

No other Warning/Error classes were found in the checked report log set
(`reports/20260628_194720`, `reports/20260628_200522`,
`reports/20260629_010651`, and `reports/20260629_023642`).

## Finding

`Animator` FBX conversion was under-loading dependencies when the CLI was run
with an explicit type filter such as:

```bat
--export_type Convert --types Animator:Both
```

Explicit `--types` replaces the default parse/export surface. Before this pass,
the CLI only auto-added parse-only `GameObject` for `Animator` export. That was
not enough for `ModelConverter`, which needs the linked hierarchy and render
payloads:

```text
GameObject, Transform, RectTransform, MeshFilter, MeshRenderer,
SkinnedMeshRenderer, Mesh, Texture2D, Material, Avatar,
AnimatorController, AnimatorOverrideController, AnimationClip
```

Without those parse dependencies, some real mesh-bearing Animators were exported
as `.fbx.empty.json` no-mesh markers.

## Implemented

AnimeStudio CLI now auto-adds the required parse dependencies when explicit
`GameObject` or `Animator` export is requested. Dependencies are added as
parse-only unless the user explicitly requested export for that type.

The parent wrapper `scripts/export_full_from_game.py` now passes the same
Animator convert parse dependencies, so map/filter selection includes the
related hierarchy and mesh objects in wrapper-driven asset exports.

The normal true-empty Animator case still writes `.fbx.empty.json` markers. It
is not silently dropped.

## Focused Validation

Historical warning sample chunk:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk
```

### Before / Animator Only

Command:

```bat
AnimeStudio.CLI.exe <chunk> tmp\animator_no_mesh_probe_nomap_20260630 ^
  --game ArknightsEndfield --logger_flags Warning Error ^
  --group_assets ByType --map_op None ^
  --export_type Convert --types Animator:Both
```

Result before the dependency fix:

- `.fbx` outputs: 0.
- `.fbx.empty.json` markers: 31.
- marker parse errors: 0.

### Manual Dependency Proof

Adding the dependency list manually recovered geometry:

- `.fbx` outputs: 5.
- `.fbx.empty.json` markers: 25.
- `.png` texture outputs: 3.
- marker parse errors: 0.

Recovered FBX files:

```text
Main.fbx
SK_actor_f.fbx
SK_actor_female.fbx
SK_actor_male.fbx
SK_actor_no_gender.fbx
```

### Auto-Fix Validation

After the CLI and wrapper changes, the plain command works without manually
listing dependencies:

```bat
AnimeStudio.CLI.exe <chunk> tmp\animator_dependency_autofix_probe_20260630 ^
  --game ArknightsEndfield --logger_flags Warning Error ^
  --group_assets ByType --map_op None ^
  --export_type Convert --types Animator:Both
```

Result:

- CLI exit code: 0.
- Warning/Error output: none.
- `.fbx` outputs: 5.
- `.fbx.empty.json` markers: 25.
- `.png` texture outputs: 3.
- marker parse errors: 0.

The auto-fix output matches the manual dependency proof exactly for the sample
chunk.

Build/syntax checks:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
python -m py_compile scripts\export_full_from_game.py
```

The CLI build succeeded. It still prints existing warnings from unrelated core
and utility projects; no new Program.cs errors were introduced.

## Current Export Output Audit

Current `export_full` already contains no-output Animator markers from earlier
runs:

| root | `.fbx.empty.json` markers | `.fbx` outputs | marker parse errors | reasons |
| --- | ---: | ---: | ---: | --- |
| `export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Animator` | 57,025 | 0 | 0 | `no_mesh` |
| `export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type/Animator` | 5,423 | 0 | 0 | `no_mesh` |

Those outputs were generated before the dependency fix and now need a targeted
refresh. The sample proof shows at least some of those markers can become real
FBX outputs once dependencies are parsed.

## Remaining Work

- Refresh `StreamingAssets:convert_by_type:Animator` and
  `Persistent:convert_by_type:Animator` with the dependency fix.
- Recount how many former no-mesh markers become real FBX outputs.
- Keep true no-mesh Animator markers as structured evidence for UI/camera/helper
  objects with no geometry.
