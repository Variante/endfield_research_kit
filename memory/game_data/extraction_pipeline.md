# Extraction: the AnimeStudio pipeline

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 1, extraction lane.** You cannot read the binary without the reader, and
this is the reader. It covers how extraction is driven, what each export scope
includes, what the provenance states mean, and how to change the exporter safely.
It does not cover what the extracted bytes mean -- that is the lane files.

AnimeStudio is the maintained extraction boundary between installed Endfield
data and the repository's builders. Production users enter through the root
wrappers; direct CLI commands are for focused recovery and diagnostics.

## Ownership

| Layer | Owner |
| --- | --- |
| Installed VFS catalog, overlay, block reads, Unity objects, conversion | `tools/AnimeStudio/` |
| Installed-game orchestration, scope, worker isolation, provenance | `scripts/game_data/extraction/export_full_from_game.py` |
| Story/Text, Map, Characters, Gameplay, Audio, Assets, Data publication | owning Python builders under `scripts/` |
| Stable CLI mechanics and VFS evidence index | `.codex/skills/animestudio-workflow/references/animestudio.md` |
| Per-build counts, hashes, failures, and audits | `reports/animestudio/` and `reports/export/` |

Do not move page semantics into AnimeStudio. Improve AnimeStudio when extraction
omits or misdecodes source bytes; improve the owning builder when extracted
evidence needs a domain join or presentation contract. The mechanics below are
documented in full in the module docstrings under
`scripts/game_data/extraction/` and in `unity_store.py`, `game_file_store.py`
and `sprite_crops.py`.

## Production export

| Goal | Command | Exported |
| --- | --- | --- |
| Text-only Story/Text refresh | `.\export.bat story --from-game` | Table and JsonData, maps, broad Story carrier JSON, object index; no media or audio |
| One page's inputs | `.\export.bat map --from-game` | exactly what that page's build tasks read (`scripts/webui/pages.py`) |
| Every page's inputs | `.\export.bat --from-game` | the union of the pages' inputs, in one AnimeStudio run; with the Data page's files that is everything |
| Everything | `.\export.bat debug --from-game` | `scope.EVERYTHING`: every structured block and Unity class |
| Synchronize the installed client and compare with the last successful sync | `.\export.bat --changed-only` | focused VFS delta plus refreshed remaining structured inputs, Unity, indexes and CN/shared audio; every page and Updates built |

An export is one `ExtractionScope` (`scope.py`): structured blocks plus Unity
JSON and Convert classes, with named levels as presets. Decoded blocks publish
into `game/`; Streaming, DynamicStreaming, IV, ExtendData, IFixPatch and the
bundle manifest publish byte-for-byte into `raw/` for the Data page only, and
recovery tools stream them from the installed client. Bundles and audio
packages are never dumped. A run publishes only its scope, so each published
block, Unity class and the asset maps carry their own installed-layer stamp
(`meta/extraction/provenance.json`), which the freshness guard checks per
declared input. MonoBehaviour and PlayableDirector are always selected
together, because the object index is merged from one run's JSON jobs.
This is complete coverage of the exporter's supported families, not a claim
that every installed object has an exact decoder or a proved semantic join.
Partial and metadata-only Unity records remain excluded with audit reasons;
raw families preserve their bytes. The wrapper publishes CN and decodes CN
Audio by default. Updates compares two complete export trees.
The low-level changed-file exporter (`export_changed_game_data.py`) compares
against its private snapshot or a certified VFS ledger bound to the previous
export summary, failing closed when the previous data cannot be authenticated.
The `--changed-only` wrapper falls back to full extraction in that case. It
refreshes the rest of the supported scope and verifies ordinary per-input
freshness, including the merged object index; a structured delta cannot make
an older Unity export current.

`EndfieldVfsLoader` supports catalog versions 1--5. Version 4 has 32-bit
chunk/file tag slots; version 5 has 64-bit slots. Unknown values retain every
bit and stay unnamed; matching their positions does not prove runtime meanings.
CRC, count, range and exact-ending checks remain required. A version rejection
occurs after decrypted-metadata CRC verification and before logical-file decoding.
Unity can scan chunk containers independently, and failed index commands can
leave old indexes on disk; neither successful Unity work nor `exists=True`
authenticates a current catalog. The full exporter records a required-index
failure and stops before overlay selection or workers, without refreshing
published provenance. Delta reader-command failures return exit code 2 and stop
the wrapper; missing baseline evidence still permits full-extraction fallback.

Per-asset Unity cache keys bind both the object's layer and all installed
fallback layers, in addition to the overlay skip list, object Hash, CLI,
DummyDll and export options. An unchanged object Hash cannot authenticate its
parsed dependencies after a fallback-layer update.

Model Convert stages additionally load the selected player's available loose
Unity built-in resource files. Their paths, sizes and hashes enter model cache
signatures and the published model type's `auxiliaryInputs`; other Unity types
retain their own stamps. The freshness guard reports missing or changed
auxiliary inputs instead of accepting an old model export. Focused repair
publication preserves the original layer stamp and changes only its resource
dependency record; it never restamps unrelated output types as freshly extracted.

The VFS dump bounds file extraction to at most eight parallel producers.
Packed `Json/LipSync` writes enqueue compression tasks on the same thread pool;
unbounded producers can fill the document store's queue and leave its writer
waiting for compression stranded on blocked producers. Keep producer
concurrency bounded when changing either side of this pipeline. The
`packed-dump-stress` CLI test runs a synthetic packed corpus with a small
thread pool and an external timeout, checking that every row is published.

`export_sync.py` preserves independent complete export snapshots under
`reports/export/sync/`: mutable files and decoded audio are copied, SQLite
stores use the backup API, and converted Unity media can be hardlinked because
publication unlinks each old file before replacement. Only snapshots with the
matching ownership receipt are pruned. The current export, the next comparison
baseline and the previous comparison's old side remain available. Source
identity is checked again before commit; a failed run retains its old baseline
so retrying cannot compare against a half-published export. The Story guide
consumer reports an incomplete object-index validator's original failure and
expected source fingerprint before trying to use its merged path.

**Lua** is not a Story input: it ships with the Data page and every all-page
run, and the Mission Pipeline consumes the index built from it. The exporter
removes the base64+XXTEA wrapper and writes `game/Lua/<name>.lua`. A hotfix
module can carry a second authored class definition: in the current client
`Data/LuaScripts/Common/Core/LuaHotFixCode.lua` reassigns
`InventoryCtrl = HL.Class(...)` with phase-level/depot refresh methods and a
changed phase-level message target, and the Wuling parkour settlement
controller shows the current pass time while keeping best time for the record
check. These are source-level UI facts, not a new wrapper; a definition does
not prove the module loaded or an event fired, and none of the three changed
modules calls a Story playback API. The older decoded export cannot be
rewrapped uniquely after newline normalization, so only the current
raw-MD5/strict-decoder/export chain counts. The Mission Pipeline Lua consumer
report predates it and must be regenerated from a complete current Lua export
before its Story references count as current.

## Build and direct CLI use

```bat
git submodule update --init tools/AnimeStudio
.\scripts\game_data\extraction\animestudio\setup_dotnet9.bat
.\scripts\game_data\extraction\animestudio\setup_vgmstream.bat
.\scripts\game_data\extraction\animestudio\rebuild.bat -Target CLI
.\scripts\game_data\extraction\animestudio\rebuild.bat -Target CLI -NoRestore
```

The executable is
`tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe`.
Use direct `dump`, `audio`, `stream`, `vfs-index`, or `list` only for a bounded
probe, and read each subcommand's `--help`. Audio defaults to direct lossless
FLAC, piped from the pinned repo-local vgmstream with no WAV and no `ffmpeg`.

Targeted Texture2D native-payload export preserves authored compressed mip
chains. BC5 and BC7 layouts validate block-rounded mip ranges and exact payload
length, and malformed supported layouts fail closed; other formats may keep raw
bytes with an explicitly unvalidated layout. A top-level PNG alone is not
render parity: consumers must verify the manifest and imported mip bytes.

## Export root layout (v4)

`ExportLayout` (`scripts/source_paths.py`) owns every export path, and
`layout.json` (`state` writing|complete) gates every reader.

- `game/` is one effective tree of exactly decoded data: `Table Json Video
  Terrain Lua` without the VFS `Data/` prefix, `Audio/<LANG|shared>`,
  `Unity.sqlite` (object documents), `GameFiles.sqlite` (`PACKED_GAME_DIRS`),
  and converted media under `Unity/<Type>`; Sprite is a crop-document row over
  its Texture2D ([`unity_assets.md`](unity_assets.md)). Animator `.fbx` is a
  store row too: each cutscene bundle re-exports the characters it carries, so
  the same meshes repeat across files; FBX property blocks of
  `FBX_CHUNK_MIN` bytes or more are stored once in `chunks` (37 chen exports:
  373 MB loose, 35 MB packed). The FBX SDK stamps every write with a time,
  random ids and the file name, so the store keeps each FBX normalized
  (`scripts/game_data/fbx_normalize.py`): equal content is equal bytes and one
  SHA256, and only content that really differs (per-cutscene prefab variants)
  stays distinct. Stores have no loose
  fallback; `pack_export_stores` upgrades a v2/v3 root and
  `migrate_export_layout` a v1 root, with rollback.
- `meta/<Layer>/...`, `meta/cab_map` and `meta/extraction/` stay per layer,
  because the base catalogue is what proves a replacement.
- The Persistent block manifest resolves each logical file; each layer's Unity
  run skips its superseded bundle slots, and every extraction regenerates both
  layers' VFS indexes first (`unity_overlay.py`). A migrated root's raw
  per-layer object index must be filtered to effective slots.
- Asset sources nest (`Game` contains `Unity` and `Audio`, pruned by
  `prune_nested_source_dirs`). Logical VFS paths reach disk only through
  `ExportLayout.game_file`, never `game / logical`.
- Builder output never lands here (`webui/data/_build/`); Updates diffs `game/`.

## Export model and provenance

Keep these states distinct: indexed, loaded, exported, partial, and certified
clean. A zero exit code or wrapper stage success does not certify every object.
Every claim keeps its source root and physical identity: Unity references use
source/CAB plus PathID, never a PathID or normalized name alone. Persistent
overlays StreamingAssets while retaining fallback chunk resolution. Missing
dependencies, ambiguous external targets, malformed objects, and unsupported
schemas remain explicit.

For a combined VFS audit, priority is positional despite the option's name:
pass Persistent as `--streaming-assets` (the primary root) and StreamingAssets
as `--fallback-assets`. The loader recognizes a newer compatible primary
metadata catalog as a replacement. Reversing these roots puts the newer
catalog in fallback and correctly yields `conflicting_metadata`; this does
not by itself establish corrupted metadata. Audit the intended overlay order
before attributing a combined census failure to the exporter or game bytes.

**Exact-only output.** Non-exact sub-trees become `$undecoded` stubs; partial,
metadata-only and TypeTree-less objects are not written, and the export
manifest records every write and exclusion with its reason. A partly recovered
`SerializeReference` payload is re-decoded additively from the file's own
`m_RefTypes` TypeTree, fail-closed, recording `exactTypeTreeUpgradeFailure`
otherwise. That upgrade keeps every `data_projectile_*` object and each
template with a populated `deadEffect`: a JSON export from an older CLI has no
projectile objects, and the fix is re-running the MonoBehaviour `json_by_type`
stage with a rebuilt CLI, not adapting a consumer.

**Three exported types carry no provenance.** MonoBehaviour, PlayableDirector
and AnimatorController carry an `$animestudio` block with `sourceFile`, and
Animator carries the same fields at top level; **Material, TextAsset and
AnimatorOverrideController carry none.** A cross-file `PPtr` resolves only
through the referrer's container ([`containers_cabmap.md`](containers_cabmap.md)).
Material texture references are about 98% cross-file and `m_Texture.Name` is
empty in every material, so the name-first branch in
`scripts/webui/assets/index.py` never fires and the published
material-to-texture links rest on a global PathID match alone: probably right,
since PathIDs are measured unique in this export, but uncheckable. The fix
belongs in the exporter. The AnimeStudio fork emits the block for every typed
asset class (validated on a bounded dump; see `scripts/game_data/cabmap.py`),
but the export has not been rebuilt, so a builder must tolerate its absence.

**An Animator FBX needs its dependency bundles loaded.** A character's
SkinnedMeshRenderers usually point at Mesh objects in another bundle; exported
alone, `ModelConverter.GetMesh` gets null and AnimeStudio silently drops the
renderer (a cutscene actor came out as hair only). The wrapper therefore runs
the AssetMap-unsafe types (Animator, GameObject, AnimatorController,
AnimatorOverrideController) with `--map_op CABMap,Load` when the layer's CAB map
exists; the CLI loads dependencies only to resolve PPtrs and exports just the
primary file's objects (`SelectPrimaryFiles`). It costs several times the load
time per bundle.

Dependency loads also pass the other installed layer's CABMap as
`--fallback_cab_map`. The selected layer remains authoritative for duplicate
CAB names; the fallback fills only absent names and preserves its own source
root. Dependency offsets must be retained even inside the selected input
chunk, because a filtered run otherwise omits same-chunk renderer resources.
The loader normalizes dependency paths and rejects malformed supplied maps
before using them. The cat attachment is a verified example: a layer-only
export retained fur and skeleton while omitting body/secondary meshes; the
patched two-layer load retained every declared mesh across its LODs.
This fixes dependency discovery, not shader deformation or runtime appearance.

Animator conversion accounts for meshless results with a
`.fbx.empty.json` document whose `animeStudio.reason` is `no_mesh`. This proves
only that the converter resolved no mesh, not that the prefab has no particles,
camera behavior or other presentation. `TryExportFile` reserves the `.fbx`
path before that decision, so a manifest can contain both the proposed `.fbx`
row and the actual marker. Count actual FBX store rows separately from markers;
a clean output-accounting result is not a complete skill-presentation claim.

**Rebuilding the CLI** can change the VFS audit's `inputSetSha256` (what it
fingerprints is stated in `AGENTS.md`), so rerun the full audit and rebind
dependent corpus gates deliberately. It records the CLI apphost EXE, not every
implementation DLL, so an assembly-only change also needs a decoder-closure
check.

An audit made with a retained CLI copy binds corpus streaming to that recorded
path. Pass the copy through the gate's `--cli` option when reusing its audit;
an identical apphost at the default path does not replace the recorded build
input. The Buff gate checks this identity before native validation and reports
the selected path and hash beside the bounded recorded build inputs. Its
before/after decoder-closure checks still authenticate the accompanying DLLs.

**Diagnostics.** The optional object index fails closed on any incomplete or
stale part (`animestudio_index_io.py`). Read
`reports/export/export_full_summary.md` first, then
`reports/export/{runs/<timestamp>,benchmarks}/` and the root's
`meta/<Layer>/{asset_status,export_manifest}/` and `meta/extraction/failures/`.
An `Export <Type>:<Name> error` may be object-local even when the process
continues; a nonzero subprocess return code fails the wrapper. Metadata-only or
`$partial` output is useful evidence, not a completeness claim.

## Scheduling and memory

Each default was measured; the figures are in `export_full_from_game.py`.
Re-measure before changing one.

- `--animestudio-type-job-mode auto` shards map-filtered Convert types
  (CPU-bound, scales), runs broad Story JSON types sequentially in isolated
  processes (bound on small-file creation, does not scale), and keeps
  MonoBehaviour and PlayableDirector broad. `--animestudio-broad-json-jobs`
  stays at 1; lower `--asset-jobs` first when memory is tight.
- Map filtering holds only TextAsset. Add a type only after broad and filtered
  outputs match byte for byte: a filtered load never opens skipped bundles, so
  equal counts prove nothing. MonoBehaviour was rejected (MonoScript names and
  external PPtr targets lost); PlayableDirector has no map entries.

## DummyDll and MonoBehaviour schemas

```bat
python -m scripts.game_data.extraction.animestudio.generate_dummydll --dry-run
python -m scripts.game_data.extraction.animestudio.generate_dummydll --replace
python -m scripts.game_data.extraction.animestudio.generate_dummydll --status-only
```

DummyDll generation is tied to the exact installed `GameAssembly.dll` and
`global-metadata.dat`; never reuse registration addresses from another build.
Its publication gates and the Cpp2IL rules it depends on are in
`generate_dummydll.py`. Endfield Cpp2IL compatibility is source in
`Variante/Cpp2IL-Endfield` on `endfield/2022.0.7`, consumed as an immutable
pinned release, never a local patch. The selected v29 TypeDef row carries one
extra, semantically unnamed int32; a retained-byref prefix reading of it is
disproven. The safe TypeTree priority is `serialized-first` (`script-first`
only for a focused comparison); missing or stale DummyDlls warn and fall back.
DummyDlls provide names, inheritance, and possible field shapes -- not method
bodies or proof that a type was emitted -- and managed-reference registries
and recovered semantic readers keep their own exact-consumption gates.

## Shader recovery

AnimeStudio owns the shader-container, bytecode-sidecar, metadata, and SPIR-V
readable-output path through the dependency-free `AnimeStudio.ShaderRecovery`
project. The former Ruri dependency is retired; keep its historical local
artifacts only as comparison provenance until AnimeStudio-owned semantic
fixtures cover the high-value character, effect, deferred, shadow, and
clearcoat cases and verify bindings, constant buffers, entry points, I/O
semantics, compilation, and source hashes. Do not copy AGPL source; a new
translator dependency needs license and target-framework review.

## Change and verification workflow

1. Find the smallest failing source, stage, type, or payload family.
2. Keep the raw object/request as a focused fixture under the owning test
   project; revisitable probes go in `scratch/animestudio/<task>/`.
3. Patch the narrow parser/exporter boundary with positive and negative tests.
4. Rebuild the CLI, rerun the smallest affected export, inspect object-level
   diagnostics; run broad extraction only when focused parity passes.
5. Record only durable conclusions here; inventories and hashes go to reports.

## Empty Mesh outputs

A zero-vertex Mesh OBJ can represent a successfully parsed collision-only,
baked Unity Mesh. Focused raw probes in separate source CABs consumed the
complete modern Endfield Mesh objects: render vertex/index buffers and the
stream payload were absent, while the baked triangle collision buffer was
populated. `Mesh.cs` skips compressed render data and triangle assembly
when the serialized baked flag is set (see
[`Mesh.cs`](../../tools/AnimeStudio/AnimeStudio/Classes/Mesh.cs));
[`Exporter.ExportEmptyMesh`](../../tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs) preserves
the identity as a diagnostic OBJ. An Assets no-geometry tag also includes meshes
with vertices but no faces; it must not imply every tagged object is baked or
has zero stored positions. Typed/raw joins and generic Dumps distinguish baked
collision geometry, point stubs, index-free FX meshes and a baked object whose
two cooked buffers are themselves empty.
The generic embedded-type-tree Dump/ToType reader projects out the
`m_CompressedMesh` subtree only for Endfield Mesh objects whose serialized
`m_CollisionMeshBaked` prefix is true. It preserves the shared tree and requires
complete object consumption for that branch; malformed/trailing data still
fails. The typed reader was already correct about that omission. Mesh JSON,
empty OBJ markers and no-output warnings retain the collision flags and bounded
cooked-buffer diagnostics (byte count, header, SHA256), without retaining all
cooked buffers in memory during bulk export.

The cooked buffers match the versioned framing of NVIDIA's
[PhysX triangle writer](https://github.com/NVIDIAGameWorks/PhysX/blob/4.1/physx/source/physxcooking/src/mesh/TriangleMeshBuilder.cpp),
[serialization flags](https://github.com/NVIDIAGameWorks/PhysX/blob/4.1/physx/source/geomutils/src/mesh/GuMeshData.h)
and [stream header](https://github.com/NVIDIAGameWorks/PhysX/blob/4.1/physx/source/geomutils/src/GuSerialize.cpp).
The maintained readers consume the complete observed cooked buffers, with
contiguous byte-span accounting and independent geometry checks:

- [`cooked_collision.py`](../../scripts/game_data/cooked_collision.py) owns
  version-15 `NXS`/`MESH`: positions, cooked-order triangle indices, optional
  materials, original-face remap and adjacency framing, BV4 version-3 quantized
  or float slabs, local sphere/bounds, geometric epsilon and per-triangle edge
  masks. Every active BV4 node is reachable, and leaves cover cooked triangles
  exactly once. Index widths follow serialization flags; remap width follows
  the stored maximum. The edge byte names silhouette bits 0–2 and convex bits
  3–5 in triangle edge order 01/12/20. RTree, GPU tails and other versions fail
  closed; `--prefix-only` explicitly retains the earlier partial probe.
- [`cooked_convex.py`](../../scripts/game_data/cooked_convex.py) owns version-13
  `NXS`/`CVXM`, version-9 `ICE`/`CLHL`: hull vertices, polygon planes and loops,
  minimum-projection indices, edge/vertex face maps, optional GPU endpoints,
  bounds, mass, inertia, center and internal sphere/box. Closed oriented edge
  topology and Euler checks agree with stored maps. Independent volume
  integration reproduces unit-density mass, center and **origin** inertia;
  treating the stored tensor as center inertia is wrong. Optional `SUPM`/`GAUS`
  version 0 and `VALE` version 2 encode cubemap minimum/maximum support vertices
  and valency lists; every sample agrees with hull extrema and every adjacency
  list with polygon edges.

Numerical details matter. PhysX's quantizer truncates small negative minima to
zero and does not decrement that zero word; only this exact branch receives
one stored dequantization unit of lower-bound allowance. Independently rounded
parent/child bounds receive two units. Convex planes can have small residuals
against their polygon vertices: the source hull checker uses a scale-dependent
cooking tolerance, so exact coplanarity is not promised. Internal sphere/box
heuristics reproduce the [convex writer](https://github.com/NVIDIAGameWorks/PhysX/blob/4.1/physx/source/physxcooking/src/convex/ConvexMeshBuilder.cpp)
only when float32 operation boundaries are preserved; float64 cancellation
changes the limiting box for nearly axis-aligned planes.

[`cooked_collision_corpus.py`](../../scripts/game_data/cooked_collision_corpus.py)
owns the reusable selected-corpus gate. It validates the VFS ledger and expected
input-set fingerprint, authenticates selected Bundle chunks and metadata/native
inputs, snapshots the full exporter output closure, performs a fresh typed/raw
Mesh extraction and requires exact serialized-identity coverage. Each cooked
buffer must have a unique raw length/SHA256/header match before decoding to EOF.
The selection defines coverage, not all installed Meshes. A scoped Bundle audit
can validate a primary-layer selection without certifying the full overlay.
The combined current audit uses Persistent first. Its ledger retains shadowed
fallback declarations; the selected-corpus gate admits only active verified
rows, so a shadowed file cannot satisfy coverage or duplicate an active chunk.
Version-2 receipts derive the Unity export input directory from authenticated
physical source chunks, allowing selected fallback chunks beneath an overlaid
catalog. Version-1 single-root receipts remain readable with their original
input-directory check. Saved receipts are reusable only while the metadata,
native inputs, physical chunks and exporter closure still agree. Inventories,
hashes and run receipts stay in
`reports/assets/cooked_collision_current_latest.json` and `reports/animestudio/`.

This establishes stored collision surfaces and acceleration/physical-property
metadata. Runtime collider ownership, selected transforms/scales, renderer
materials and collision behavior remain separate joins. Collision OBJs retain
local coordinates and winding and are not published as render replacements.

## Remaining gaps

- Export coverage for separately declared language LipSync catalogs. Unknown
  catalogs with absent payloads remain full-audit failures; optional-language
  availability needs its own proven contract before changing that gate.
- Per-object clean/partial/error certification and dependency diagnostics.
- Rebuild the CLI and re-export so Material/TextAsset/AnimatorOverrideController
  provenance reaches consumers, then re-run the invalidated corpus gates.
- More exact MonoBehaviour and managed-reference schemas. The `m_RefTypes`
  upgrade closed every non-empty undecoded managed-reference payload in its
  measured slice; what remains is the hand-written decoders it did not replace
  and types whose RefTypes entry is absent or not unique.
- Shader-container coverage, semantic shader fixtures, and converter
  regressions for more Unity layouts.
- Lower peak memory for broad Story JSON/object-index work without unsafe
  filtering or unsupported JSON concurrency.
