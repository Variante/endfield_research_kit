# Extraction: the AnimeStudio pipeline

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 1, extraction lane.** You cannot read the binary without the reader, and
this is the reader. It covers how extraction is driven, what each export scope
includes, what the provenance states mean, and how to change the exporter safely.
It does not cover what the extracted bytes mean -- that is the lane files.

AnimeStudio is the maintained extraction boundary between installed Endfield
data and the repository's builders. Production users should enter through the
root wrappers; direct CLI commands are for focused recovery and diagnostics.

## Ownership

| Layer | Owner |
| --- | --- |
| Installed VFS catalog, overlay, block reads, Unity objects, conversion | `tools/AnimeStudio/` |
| Installed-game orchestration, scope, worker isolation, provenance | `scripts/game_data/extraction/export_full_from_game.py` |
| Story/Text, Map, Characters, Gameplay, Audio, Assets publication | owning Python builders under `scripts/` |
| Stable CLI mechanics and VFS evidence index | `.codex/skills/animestudio-workflow/references/animestudio.md` |
| Per-build counts, hashes, failures, and audits | `reports/animestudio/` and `reports/export/` |

Do not move page semantics into AnimeStudio. Improve AnimeStudio when extraction
omits or misdecodes source bytes; improve the owning builder when extracted
evidence needs a domain join or presentation contract.

## Production export

| Goal | Command | AnimeStudio scope |
| --- | --- | --- |
| Refresh Story/Text | `.\export.bat --from-game` | structured focused dump, maps, broad Story JSON |
| Refresh Story and assets together | `.\export.bat --from-game --with-assets` | one combined Story/asset pass |
| Apply a local client delta without publishing Updates | `.\export.bat --changed-only` | changed focused VFS files, reuse bundle-derived outputs, all WebUI builders |
| Refresh assets and CN audio only | `.\export_assets.bat --from-game` | skip structured Story, asset maps/conversion/JSON, VFS index, audio |

The focused structured dump includes Table, JsonData, and video. It excludes raw
bundles, audio packages, world streaming, irradiance, ExtendData, patch data,
and Lua. `--structured-dump-mode default` additionally includes the maintained
Terrain height subset; `debug` is for broad diagnosis.

Changed-only export keeps a private, export-root-local logical-file snapshot
and compares decoded FileDataMd5 plus length/type/path/encryption identity. It
uses exact full-path dump filters for changed structured files, validates the
staged output set, and handles deletions explicitly. The first post-update run
may seed the old side only from a certified VFS ledger whose input set and
physical inventory bind to the previous export summary; otherwise it fails
closed and requires a full export. Bundle-derived maps, objects, assets, and
audio are refreshed broadly because a changed bundle does not prove safe
per-output ownership. The snapshot commits only after the complete WebUI
pipeline succeeds, and this local mode never reads or writes Updates state.

Asset modes are intentionally ordered:

- `focused`: WebUI-referenced Texture2D media only.
- `default`: WebUI-facing image/model/material/animation outputs and audio
  callback ownership inputs.
- `debug`: broad conversion and JSON types for investigation.

After extraction, page builders consume `export_full/`; see
[`webui_recovery.md`](../webui_recovery.md) for the complete publication flow.

## Build and direct CLI use

Targeted Texture2D native-payload export preserves authored compressed mip chains.
BC5 and BC7 layouts validate block-rounded mip ranges and exact payload length;
malformed supported layouts fail closed. Other formats may retain raw bytes with
an explicitly unvalidated layout. A decoded top-level PNG alone is insufficient
for render parity; consumers must verify the manifest and imported mip bytes.

```bat
git submodule update --init tools/AnimeStudio
.\scripts\game_data\extraction\animestudio\setup_dotnet9.bat
.\scripts\game_data\extraction\animestudio\setup_vgmstream.bat
.\scripts\game_data\extraction\animestudio\rebuild.bat -Target CLI
.\scripts\game_data\extraction\animestudio\rebuild.bat -Target CLI -NoRestore
```

Expected executable:

```text
tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe
```

Use direct `dump`, `audio`, `stream`, `vfs-index`, or `list` only for a bounded
probe. Inspect each subcommand's `--help`; do not maintain another option
catalog here. `dump`, `audio`, `stream`, and `vfs-index` support the sibling
root fallback. `dump`, `stream`, and `vfs-index` support repeated block-type and
file-regex filters. Audio defaults to direct lossless FLAC: the CLI pipes PCM
from the pinned repo-local vgmstream decoder into its in-process FLAC encoder,
without an intermediate WAV file or `ffmpeg`.

## Export model and provenance

Keep these states distinct: indexed, loaded, exported, partial, and certified
clean. A zero exit code or wrapper stage success does not certify every object.

Every claim keeps its source root and physical identity. Unity references use
source/CAB plus PathID; a PathID or normalized name alone is not globally
unique. Persistent overlays StreamingAssets while retaining fallback chunk
resolution. Missing dependencies, ambiguous external targets, malformed
objects, and unsupported schemas must remain explicit.

The optional object index publishes compressed object/schema streams plus a
last-written terminal `summary.json`. Consumers fail closed on missing or
incomplete summaries, stale source or CLI provenance, hash mismatch, duplicate
physical identity, or ambiguous external CAB/PathID targets. Scene hierarchy
and world positions are exact only when their resolution status says so.

Use the generated export summary first when diagnosing a run:

```text
reports/export/export_full_summary.md
reports/export/runs/<timestamp>/
reports/export/benchmarks/
export_full/recovered/AnimeStudio-cli/animestudio_type_manifest.json
export_full/recovered/AnimeStudio-cli/<source>/asset_status/
export_full/unresolved/
```

An `Export <Type>:<Name> error` may be object-local even when the process
continues. A nonzero subprocess return code fails the wrapper. Metadata-only or
`$partial` output is useful evidence, not a completeness claim.

## Scheduling and memory

The measured default is `--animestudio-type-job-mode auto`:

- map-filtered conversion types may use balanced shards;
- broad Story JSON types run sequentially in isolated processes;
- MonoBehaviour and PlayableDirector remain broad;
- JSON export is not sharded or broadly concurrent.

Add a type to map filtering only after broad and filtered outputs match
byte-for-byte. Equal object counts are insufficient because skipped bundles can
remove script definitions or external PPtr targets. Lower `--asset-jobs` before
changing shard counts or architecture when memory is constrained.

## DummyDll and MonoBehaviour schemas

```bat
python -m scripts.game_data.extraction.animestudio.generate_dummydll --dry-run
python -m scripts.game_data.extraction.animestudio.generate_dummydll --replace
python -m scripts.game_data.extraction.animestudio.generate_dummydll --status-only
```

DummyDll generation is tied to the exact installed `GameAssembly.dll` and
`global-metadata.dat`. The generator must uniquely recover registrations,
validate a complete staged managed image set, publish atomically, preserve the
previous set, and record provenance in `tools/DummyDll/generation.json`. It
must reject any type-population failure, required-image skip, and catastrophic
type/size regression by default, and must join every staged non-module TypeDef
to the selected metadata on assembly, token, and full name before publication.
Endfield Cpp2IL compatibility is maintained as source in
`Variante/Cpp2IL-Endfield` on `endfield/2022.0.7`; the generator consumes an
immutable release pinned by tag and commit instead of applying a local patch.
The checkout is tracked as the optional `tools/Cpp2IL-Endfield` submodule;
`setup.bat` does not initialize it, while the DummyDll generator initializes it
on demand for script-schema recovery. A pinned commit is insufficient by
itself: both preparation and validation also reject a foreign origin or tracked
local changes.
Never reuse registration addresses from another build.

Cpp2IL must attach a method shell and predeclare every method generic parameter
in metadata order before importing constraints, return types, or parameters.
Importing an MVAR-bearing return through the declaring type fails, while lazy
return-first parameter creation can silently reorder multi-generic signatures.
Commit global method maps only after signature construction succeeds and roll
back the shell plus newly registered parameters on failure.

The selected v29 build uses exact 92-byte TypeDef rows: the prefix is the stock
v29 layout, while one additional int32 occurs after the eight range-start
fields and before the ushort counts. Keep that slot semantically unnamed. The
image ranges, all eight start/count families, nested-child relationships, and
token sequences close exactly under this boundary; a retained-byref prefix
interpretation is disproven.

The safe TypeTree priority is `serialized-first`. Use `script-first` only for a
focused comparison. Missing, stale, malformed, or incomplete DummyDlls warn and
fall back without breaking a normal export. DummyDlls provide names,
inheritance, and possible field shapes—not method bodies or proof that a type
was emitted. Managed-reference registries and recovered semantic readers retain
their own exact-consumption and type gates.

## Shader recovery

AnimeStudio owns the maintained shader-container, bytecode-sidecar, metadata,
and SPIR-V readable-output path through the dependency-free
`AnimeStudio.ShaderRecovery` project. The former Ruri runtime/build dependency
is retired; keep historical local artifacts only as comparison provenance.

Do not remove that provenance until AnimeStudio-owned semantic fixtures cover
the high-value character, effect, deferred, shadow, and clearcoat cases and
verify bindings, constant buffers, entry points, I/O semantics, compilation,
and source hashes. Do not copy AGPL source. Any new translator dependency must
pass license and target-framework review for AnimeStudio's .NET targets.

## Change and verification workflow

1. Identify the smallest failing source, stage, type, or payload family.
2. Preserve the raw object/request as a focused fixture under the owning test
   project; keep revisitable probes in `scratch/animestudio/<task>/`.
3. Patch the narrow parser/exporter boundary and add positive and negative tests.
4. Rebuild the CLI, rerun the smallest affected export, and inspect object-level
   diagnostics.
5. Run broad extraction only when focused parity passes and publication needs it.
6. Update this file only for durable conclusions; publish inventories and hashes
   to reports.

## Remaining gaps

- Improve per-object clean/partial/error certification and dependency diagnostics.
- Recover more exact MonoBehaviour and managed-reference schemas.
- Expand shader-container coverage and complete semantic shader fixtures.
- Add converter regressions for more Unity layouts.
- Reduce peak memory for broad Story JSON/object-index work without unsafe
  filtering or unsupported JSON concurrency.

## Measured scheduling conclusions

Each of these was measured, not assumed, and each is the reason a knob has the
default it has. Re-measure before changing one; do not re-derive it.

The default exporter mode is
`--animestudio-type-job-mode auto`: it merges map-filtered JSON, runs broad Story
JSON types sequentially in isolated processes, and keeps map-filtered asset
conversion sharded; use `parallel` only when comparing concurrent per-type jobs.
`TextAsset` loads through the generated asset map instead of every bundle:
byte-identical output, 508s -> 27s (475,588 bundle containers parsed -> 16,218).
Every other json type still loads broadly. Map filtering is only sound for a
type that resolves nothing outside its own bundle, because the filtered load
never opens the skipped bundles -- matching object counts prove nothing.
`MonoBehaviour` has complete map coverage and was still rejected: filtering
renamed 128,181 of 174,133 files to `MonoBehaviour#100001_p...` because the
defining MonoScript sits in a skipped bundle, and turned 2,709 resolved PPtr
targets into `external_target_unavailable`. `PlayableDirector` has zero map
entries and would emit nothing. Add to `ANIMESTUDIO_JSON_MAP_FILTER_TYPES`
only after exporting a type both ways and diffing the bytes;
`--no-animestudio-json-map-filter` forces the broad path. Sharding those loads was separately measured and rejected: on identical object sets, `Convert` Texture2D scales
4.03x across 8 shards while `JSON` Material runs 0.92-0.95x, i.e. no better
than one process. Convert is CPU-bound decode (~37 ms/object); JSON export is
~3.55 ms/object and bound on single-disk small-file creation, so extra
processes only contend. Keep `convert_by_type` sharding; do not add JSON
sharding. `--animestudio-broad-json-jobs N` bounds concurrent broad loads and
defaults to 1; values above 1 are not supported by any measurement.
