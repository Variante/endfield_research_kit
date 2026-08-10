# AnimeStudio recovery

## Current status

The tracked `tools/AnimeStudio` fork is a reliable extraction layer. It can:

- index StreamingAssets and Persistent VFS roots;
- dump or stream selected blocks;
- build compact VFS and asset indexes;
- export WebUI-facing Unity objects;
- decode Wwise media;
- preserve PPtr/source-offset evidence;
- export selected shader bytecode and material state;
- retain useful partial MonoBehaviour output.

Remaining work is certification and semantic depth, not basic access.

## Maintained workflow

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI

.\export.bat --export-from-game
.\export.bat --export-from-game --with-assets
.\export_assets.bat --export-from-game
```

Expected CLI:

```text
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
```

Direct CLI use is for bounded diagnostics:

```bat
AnimeStudio.CLI.exe dump --help
AnimeStudio.CLI.exe stream --help
AnimeStudio.CLI.exe vfs-index --help
AnimeStudio.CLI.exe audio --help
AnimeStudio.CLI.exe list --help
```

Both VFS roots must be configured as fallbacks. Missing block metadata or
chunks is an integrity error, not an omitted file.

## Export model

Keep these states distinct:

- **indexed:** VFS file exists;
- **loaded:** Unity container/object entered the parser;
- **exported:** output or intentional empty marker was written;
- **partial:** useful evidence exists but decoding is incomplete;
- **certified clean:** explicit status proves no unexplained warning, missing
  dependency, or conversion failure.

Success of a wrapper stage does not certify every asset bundle or object.

The normal type-job mode is `auto`: broad Story JSON types run in isolated
processes while map-filtered asset conversion remains sharded. Reduce
`--animestudio-jobs` when RAM is constrained.

Endfield-native HGGraphics class IDs recovered from the installed UnityPlayer
are named directly (`HGTree`, `HGTreeData`, `HGMeshRenderer`, and
`HGMeshRendererData`). An explicitly selected export-enabled generic TypeTree
class is retained in a minimal AssetMap; unselected generic objects remain
omitted, so normal production map scope does not widen.

## Important boundaries

- Combined Story+asset export must keep Story JSON broad; asset-map filtering
  can omit valid DialogTree sources.
- PPtr identity is source/CAB scoped.
- `$partial` objects remain queryable and visibly incomplete.
- Material JSON preserves keywords, queues, tags, instancing, and disabled
  passes.
- Shader bytecode recovery does not prove runtime variant selection.
- AnimationClip fixes must preserve runtime curves and fail visibly on new
  layouts.
- Audio decoding separates shared media from language voice.
- The CLI intentionally stops at WEM or decoded WAV: `build_audio.py` now uses
  the WAV path as an intermediate and converts browser-facing output to
  lossless FLAC with `ffmpeg`, deleting the temporary WAV only after an atomic
  replacement succeeds. FLAC preserves decoded PCM samples and reduces disk
  use substantially, but unusual source channel layouts have produced
  converter metadata warnings and need a dedicated layout audit before being
  called fully certified.
- Projectile managed references use current IL2CPP field order plus guarded
  path-plus-id/id-only gameplay-tag variants. A projectile component is marked
  exact only when its full prefix, movement dictionary, effect lists, alert,
  sound tail, and final scalars consume the managed-reference boundary.

## Diagnostics

Check:

```text
reports/export/export_full_summary.md
reports/export/runs/
export_full/recovered/AnimeStudio-cli/animestudio_type_manifest.json
export_full/recovered/AnimeStudio-cli/<source>/asset_status/
export_full/unresolved/failed_to_decode.txt
export_full/unresolved/manifest_reference_missing.txt
```

## Remaining gaps

- Per-asset-bundle clean/partial/error certification.
- More managed-reference and MonoBehaviour schemas.
- Broader exact shader-container and program metadata support.
- Additional converter regression fixtures across Unity variants.
- Lower peak memory for large broad JSON/export jobs.
- Clearer object-level diagnostics when dependencies or conversion fail.
