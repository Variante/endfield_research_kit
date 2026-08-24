# AnimeStudio recovery

## Current status

The tracked `tools/AnimeStudio` fork is the maintained extraction layer. It can
index both VFS roots, dump or stream selected blocks, build asset/object indexes,
export WebUI-facing Unity objects, decode Wwise media, preserve PPtr and source
offsets, and retain useful partial MonoBehaviour/material/shader/animation data.

Installed Story indexes are complete and hash-validated. Remaining work is
certification, schema depth, and peak-memory reduction rather than basic access.

## Maintained workflow

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI

.\export.bat --from-game
.\export.bat --from-game --with-assets
.\export_assets.bat --from-game
```

Expected CLI:

```text
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
```

Direct CLI commands are for bounded diagnostics:

```bat
AnimeStudio.CLI.exe dump --help
AnimeStudio.CLI.exe stream --help
AnimeStudio.CLI.exe vfs-index --help
AnimeStudio.CLI.exe audio --help
AnimeStudio.CLI.exe list --help
```

`dump`, `stream`, and `vfs-index` accept repeated `--block-type` and
`--file-regex` filters. Both VFS roots must be available as fallbacks; missing
declared chunks or block metadata is an integrity error.

## Export model

Keep these states distinct:

- **indexed:** the VFS entry exists;
- **loaded:** its Unity container/object entered the parser;
- **exported:** output or an intentional empty marker was written;
- **partial:** useful evidence exists but decoding is incomplete;
- **certified clean:** explicit status found no unexplained warning, missing
  dependency, or conversion failure.

A successful wrapper stage does not certify every object or bundle.

The default type-job mode is `auto`: broad Story JSON types run sequentially in
isolated processes, while map-filtered conversion stays sharded. Map filtering
is valid only after broad and filtered outputs are byte-identical. MonoBehaviour
and PlayableDirector remain broad because their dependency/map coverage does not
support filtered export. Current measurements do not support JSON sharding;
small-file disk contention outweighs parallelism.

The normal WebUI structured dump includes tables, JSON data, and video while
skipping raw bundles, audio packages, world-streaming bytes, irradiance, patch
bytes, and Lua. Asset-only refresh uses `--skip-structured` and a lightweight
VFS index. Debug mode is for broad VFS diagnostics.

The default asset scope publishes AnimationClip conversion and
AnimatorController/AnimatorOverrideController JSON for Audio callback ownership.
Controller JSON deliberately uses broad dependency loading because filtered
type-only loads cannot guarantee resolved cross-bundle clip/controller PPtrs.

## Stable boundaries

- Combined Story+asset export keeps Story JSON broad; map filtering can omit
  valid cross-bundle DialogTree or script dependencies.
- Source and CAB scope are part of every PPtr/PathID identity.
- `$partial` objects remain queryable and visibly incomplete.
- Material export preserves keywords, queues, tags, instancing, and disabled
  passes; shader bytecode does not prove runtime variant selection.
- Endfield combined shader parameter records expose a fail-closed named
  constant-buffer table before their resource and descriptor sections. Shader
  sidecar metadata merges those exact field names, kinds, dimensions, byte
  offsets, and declared sizes with the serialized partial tables; opaque
  resource framing is used only to establish the unique boundary and is not
  mislabeled as a physical D3D register map.
- Animation fixes must preserve curves and fail visibly on unknown layouts.
- Shared audio and language voice use separate output roots.
- Timeline track and Director links prove authored scheduling, not activation
  or playback.
- Object-index hierarchy/world positions are exact only when their resolution
  status says so.

## Audio

The CLI streams decoded Wwise PCM into lossless FLAC by default without an
intermediate WAV or `ffmpeg`. `--format wav` and `--format wem` remain explicit
compatibility modes. Unsupported plugin media and missing historical chunks are
reported separately from playable-audio failures.

AudioDialog and related tables must merge StreamingAssets with Persistent
overlays while retaining fallback chunk resolution. Canonical links keep their
authored paths and language/shared provenance; duplicate inventory locations do
not replace them.

## DummyDll and schema recovery

```bat
python scripts\animestudio\generate_dummydll.py --dry-run
python scripts\animestudio\generate_dummydll.py --replace
```

DummyDll generation is tied to the exact installed `GameAssembly.dll` and
metadata. The generator stages and validates a complete image set before
publishing `tools/DummyDll/generation.json`. Never reuse registration addresses
from another build.

The safe default is `serialized-first`. Use `script-first` only for targeted
MonoBehaviour experiments; it must fall back cleanly when DummyDlls are absent,
stale, malformed, or incomplete.

## Diagnostics

```text
reports/export/export_full_summary.md
reports/export/runs/
reports/export/benchmarks/
export_full/recovered/AnimeStudio-cli/animestudio_type_manifest.json
export_full/recovered/AnimeStudio-cli/<source>/asset_status/
export_full/unresolved/failed_to_decode.txt
export_full/unresolved/manifest_reference_missing.txt
```

Changing counts, per-type inventories, and schema-specific proof belong in
these reports.

## Remaining gaps

- Per-bundle and per-object clean/partial/error certification.
- More managed-reference and MonoBehaviour schemas.
- Broader exact shader container/program metadata support.
- Converter regression fixtures across additional Unity layouts.
- Lower peak memory for broad Story JSON/object-index work.
- Clearer object-level dependency and conversion diagnostics.
