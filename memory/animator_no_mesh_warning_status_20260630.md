# Animator No-Mesh Warning Status - 2026-06-30

## Scope

Status pass for the remaining current stored AnimeStudio warning family:

```text
[Warning] Animator no output reason=no_mesh ...
```

The checked available logs contain 57,025 such warnings, all from:

```text
reports/20260628_194720/StreamingAssets/StreamingAssets_animestudio_convert_by_type.stdout.log
```

No other Warning/Error classes were found in the checked current report log set
(`reports/20260628_194720`, `reports/20260628_200522`,
`reports/20260629_010651`, and `reports/20260629_023642`).

## Code Status

The current AnimeStudio exporter no longer treats the normal no-mesh Animator
case as a warning during actual conversion.

Current code path:

- `Exporter.ExportAnimator(...)`
- constructs `ModelConverter` from the `Animator`;
- if `convert.MeshList.Count == 0`, deletes the transient export folder and
  writes an `.fbx.empty.json` marker through `ExportEmptyAnimatorMarker(...)`;
- the marker records the reason, source chunk, object ids, linked GameObject,
  mesh/material/texture/animation counts, and byte size.

The marker note is explicit:

```text
Unity parsed this Animator, but the resolved hierarchy has no Mesh objects, so
no FBX geometry can be emitted.
```

`LogAnimatorNoOutput(...)` remains only for the abnormal case where the marker
output path cannot be created.

## Focused Validation

Historical warning sample chunk:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk
```

Current direct conversion command:

```bat
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk" ^
  tmp\animator_no_mesh_probe_nomap_20260630 ^
  --game ArknightsEndfield --logger_flags Warning Error ^
  --group_assets ByType --map_op None ^
  --export_type Convert --types Animator:Both
```

Result:

- CLI exit code: 0.
- Warning/Error output: none.
- `.fbx` outputs: 0.
- `.fbx.empty.json` marker outputs: 31.
- marker parse errors: 0.

Representative marker:

```json
{
  "animeStudio": {
    "kind": "empty_animator_marker",
    "reason": "no_mesh"
  },
  "type": "Animator",
  "name": "lattice",
  "pathId": 40,
  "gameObjectName": "lattice",
  "gameObjectPathId": 10,
  "meshCount": 0,
  "materialCount": 0,
  "textureCount": 0,
  "animationCount": 0
}
```

## Interpretation

This warning family is now understood as expected no-geometry Animator assets,
not failed binary parsing or missing decryption. Current conversion preserves
each no-output Animator as a marker file instead of silently dropping it.

The stored `reports/export_full_summary.md` still references older logs with
the 57,025 warning lines. A full or targeted `StreamingAssets:convert_by_type:
Animator` refresh is needed before that summary can be used as proof that the
current full asset export is warning-free.

## Remaining Work

- Refresh the full Animator conversion stage or a broader shard-backed subset
  to replace stale warning logs with current marker-producing output.
- Audit suspicious no-mesh names such as character/enemy `*_postmodel` and
  `LookAtTarget` against surrounding GameObject/renderer data to confirm they
  are helper objects rather than missed mesh dependencies.
