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
| Story/Text, Map, Characters, Gameplay, Audio, Assets publication | owning Python builders under `scripts/` |
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
| Apply a local client delta without publishing Updates | `.\export.bat --changed-only` | changed focused VFS files; bundle-derived outputs reused; every page built |

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
Changed-only export (`export_changed_game_data.py`) compares against its
private snapshot or, after a client update, only a certified VFS ledger bound
to the previous export summary, failing closed to a full export otherwise; it
reuses bundle-derived outputs and never touches Updates state.

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
  its Texture2D ([`unity_assets.md`](unity_assets.md)). Stores have no loose
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

**Rebuilding the CLI** can change the VFS audit's `inputSetSha256` (what it
fingerprints is stated in `AGENTS.md`), so rerun the full audit and rebind
dependent corpus gates deliberately. It records the CLI apphost EXE, not every
implementation DLL, so an assembly-only change also needs a decoder-closure
check.

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

## Remaining gaps

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
