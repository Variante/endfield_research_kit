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

Offline recovery probes

Use the built CLI for repeatable evidence checks that do not load Unity bundles.
The commands accept plain JSONL and `.jsonl.gz` object indexes where noted; a
non-zero exit is an actionable recovery failure, not proof that the exporter
itself is broken.

```bat
set ASCLI=tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe

%ASCLI% shader-recover --input PATH_TO_SPIRV --output PATH_TO_HLSL
%ASCLI% inspect-object --index OBJECT_INDEX.jsonl --path-id PATH_ID --source SOURCE --type TYPE
%ASCLI% audit-refs --index OBJECT_INDEX.jsonl
%ASCLI% certify-index --index OBJECT_INDEX.jsonl
%ASCLI% replay --index OBJECT_INDEX.jsonl --requests RECOVERY_REQUESTS.jsonl
%ASCLI% schema-diff --left LEFT.json --right RIGHT.json
```

`shader-recover` writes deterministic HLSL plus a structured failure diagnostic
and hash when SPIR-V emission cannot proceed. `inspect-object` selects one
PathID in its source/type context. `audit-refs` reports nested resolution-status
counts and one sample per status. `certify-index` requires valid JSONL, a
terminal `{ "kind": "summary", "complete": true }` row, and reports status
counts; it is an index gate, not a claim that every object is semantically
complete. `replay` consumes one request object per line (`pathId`, optional
`source` and `type`) and fails if any request has no match. `schema-diff` compares
JSON shape (including object properties and the first array element), so equal
shape does not mean equal values. Keep request files and probe output under
`scratch/animestudio/` or a generated `reports/` topic directory.

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

## Shader recovery consolidation plan

The migration has started inside AnimeStudio: Endfield shader container parsing,
bytecode sidecars, SPIR-V decoding, and parameter-table recovery are already
AnimeStudio-owned. The metadata adapter no longer carries Ruri-specific type or
method names, and the external checkout is not an AnimeStudio project
dependency. The SPIR-V readable-output boundary is now AnimeStudio-owned and
certified on net9. The new dependency-free `AnimeStudio.ShaderRecovery` project now
owns the canonical input hash, normalized text, diagnostics, and provenance
contract used by the existing sidecar writer.

The operational dependency on `Ruri.ShaderDecompiler` is retired: the
independent, MIT-compatible `AnimeStudio.ShaderRecovery` library and tests are
inside the AnimeStudio solution. Do not copy or link Ruri's AGPL-3.0 source.
Keep the recovery layer separate from the core asset parser, but expose it
through AnimeStudio.CLI and feed it the existing shader bytecode sidecars and
metadata manifests so readable recovery can be rerun without loading bundles.
The Endminf verifier now checks AnimeStudio CLI provenance and preserved HLSL
reference fixtures only; it does not require, hash, invoke, or build the Ruri
project. The local Ruri checkout and its historical `ruri_final` artifacts are
kept intact for provenance and comparison.

Implement and certify the migration in this order:

1. define deterministic raw-bytecode, metadata, HLSL, diagnostics, and
   provenance outputs;
2. add independently implemented translation, metadata symbol injection,
   structured-cbuffer reconstruction, compatibility normalization, and
   SPIRV-Cross emission. SPIR-V-to-HLSL emission is complete; the available
   DXIL binding is net10-only and remains outside AnimeStudio's net8/net9
   target until a compatible MIT implementation is selected;
3. establish semantic fixtures for CharacterNPR skin/cloth/hair, LitEffect
   M27, the deferred resolver, screen shadows, and clearcoat, checking resource
   bindings, cbuffer layouts, entry points, I/O semantics, compile validity,
   and source hashes rather than Ruri-specific text formatting;
4. migrate maintained verifiers to AnimeStudio-owned outputs while preserving
   historical Ruri artifacts as provenance;
5. remove the standalone Ruri build, binary dependency, and update instruction
   only after every fixture and downstream verifier passes without it. The
   operational dependency is already retired; the dirty checkout remains only
   as migration provenance until the semantic fixture gate is filled.

Before implementation, verify the licenses and target-framework compatibility
of all native translator packages; the currently tested dxil-spirv managed
package is confirmed net10-only while AnimeStudio supports .NET 8/9. Keep the local
dirty Ruri checkout intact until its Endfield-specific behavior is represented
by passing AnimeStudio fixtures. Use `gpt-5.6-luna` for implementation support
and an independent review pass when that agent capability is available.

## Remaining gaps

- Per-bundle and semantic per-object clean/partial/error certification; the
  current `certify-index` and `audit-refs` probes are structural gates.
- More managed-reference and MonoBehaviour schemas.
- Broader exact shader container/program metadata support.
- Semantic shader fixtures and broader exact shader container/program metadata;
  the AnimeStudio-owned SPIR-V readable-output path and offline probes are now
  available, but the fixture gate still protects final Ruri checkout removal.
- Converter regression fixtures across additional Unity layouts.
- Lower peak memory for broad Story JSON/object-index work.
- Clearer object-level dependency and conversion diagnostics.
