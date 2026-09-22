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

`--structured-dump-mode` has three levels, each containing the one below.
`focused` (the default) dumps what the WebUI pages consume: Table, JsonData,
video and **Lua**. `default` adds the maintained Terrain height subset, about
64 MiB of Terrain's 1.19 GB. `full` adds Terrain whole, Streaming,
DynamicStreaming, IV, ExtendData, IFixPatch and the bundle manifest -- about
6.4 GB more, read only by recovery work. Before `full` existed none of those
blocks was reachable through the wrapper at all, which left a reproducible
input depending on a hand-run bounded dump.

Lua sits in the narrowest level on purpose: 1,339 files, ~16 MB decoded, and
the Mission Pipeline already consumes the index built from plaintext Lua, so
excluding it bought nothing and forced a separate extraction. The exporter
decodes the base64+XXTEA wrapper itself and writes `game/Lua/<name>.lua`.

Raw asset bundles and audio packages are a **separate axis** -- the
`--*-assets` scopes -- and no structured level carries them. (There is no
`debug` structured mode; `debug` is an asset scope.)

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

## Export root layout (v2)

`ExportLayout` (`scripts/source_paths.py`) owns every export path. A root is
`game/` (final, exactly decoded data: `Table Json Video Terrain Lua` with the
VFS `Data/` prefix dropped, `Audio/<LANG|shared>`, `Unity/<Type>`) plus
per-layer `meta/<Layer>/{vfs_index,asset_map,object_index,asset_status,export_manifest,renderer_index}`,
`meta/cab_map`, and `meta/extraction/{failures,incremental}`. `layout.json`
(`state` writing|complete) gates every reader.

- `game/` is one effective tree: the Persistent block manifest (newer version)
  resolves each logical file. The structured dump runs for that layer only;
  each layer's Unity run gets `--skip_sources_file` with its superseded bundle
  slots, so staging holds live objects only (`unity_overlay.py` fails closed on
  a missing, incomplete, or older manifest). meta stays per layer because the
  base catalogue is what proves a replacement. An object index built before
  this skip (every migrated root) still lists replaced-bundle rows, so a
  reader of a raw per-layer index keeps only rows whose (chunk, offset) slot is
  effective (`animestudio_index_io.EffectiveObjectRows`), counting every
  `object` row for its integrity check. Slots match by (chunk file name,
  offset); the catalogue loader fails closed if one name denotes two chunks.
- Staging (also the per-asset reuse cache), filters and index parts live under
  `tmp/game_data/export/<root>-<hash>/`; `game/Unity` is a hardlink mirror,
  synced per type only when every installed layer finished that type's item
  in this run, never after a failed command or a failed stage item; the
  structured tree is published only by a run that dumped the effective layer.
  Catalogues, skip lists and the dump layer always follow the installed
  layers, not the layers a run selected. Raw containers (bundles, PCKs, streaming chunks) are never dumped.
- Exact only: non-exact sub-trees become `{"$undecoded": ...}` location stubs;
  partial, metadata-only and TypeTree-less objects are not written, and the
  export manifest records every written path (CAB, chunk, offset) and every
  exclusion with its reason. Unnamed objects are named by script class.
- A `SerializeReference` payload the hand-written decoders can only partly
  recover is re-decoded from the file's own `m_RefTypes` TypeTree, which is
  exact and names every field. The upgrade is additive: an already exact
  decoder result is never replaced, so existing consumers keep reading the same
  keys, and the TypeTree route stays fail-closed on a unique RefTypes match
  plus exact payload consumption. When it cannot run, the reason is recorded on
  the node as `exactTypeTreeUpgradeFailure` instead of vanishing with the stub.
  Two rules this depends on: the trigger must be `ExactOnlyGate`'s own marker
  set, because a separate list that omits `$inferred` leaves marked content to
  be deleted by the gate and never upgraded; and the remaining zero-length
  stubs are Unity's `rid: -2` null sentinel, which has no bytes to decode and
  is not a gap. The upgrade is what keeps whole gameplay families in the
  export: the hand-written `EffectActionCfg` reader marks every entry
  `$partial` for unnamed enum semantics even though its layout is TypeTree
  exact, and the registry status treats any nested `$partial` as a partial
  object, so without the upgrade every `data_projectile_*` object and each
  AbilityEntity or character template with a populated `deadEffect` is
  excluded (the manifest's `excluded` rows with a `partial:` reason are the
  audit). A JSON export made with a CLI older than the upgrade therefore
  has no projectile objects; re-run the MonoBehaviour `json_by_type` stage
  with the rebuilt CLI rather than adapting a consumer to the missing files.
- Asset sources nest: `Game` is `game/`, which contains the `Unity` and `Audio`
  sources, so a Game walk prunes them (`prune_nested_source_dirs`). Logical
  VFS paths (`Data/Json/...`, as tables record them) reach disk only through
  `ExportLayout.game_file`, never `game / logical`.
- Builder output never lands here (`webui/data/_build/`); Updates diffs `game/`.
- `migrate_export_layout` converts a v1 root by recorded same-volume renames
  (`--dry-run`, `--rollback`), quarantining what has no v2 place; unproven Unity
  outputs block it except exporter companions and types the asset maps do not
  index, which use a bridge-only "newer layer wins by name" rule. An output
  whose chunk sits in an indexed block folder, is in neither catalogue, and is
  gone from the install is `stale` (left by a run against an older build) and
  is quarantined; a chunk outside every indexed block, or one still on disk
  (possibly newer than the catalogues), stays unproven. A type an older
  exporter wrote through both stages keeps only the stage the current exporter
  uses (TextAsset: JSON), file by file, and only where that sibling exists.

## Export model and provenance

Keep these states distinct: indexed, loaded, exported, partial, and certified
clean. A zero exit code or wrapper stage success does not certify every object.

Every claim keeps its source root and physical identity. Unity references use
source/CAB plus PathID; a PathID or normalized name alone is not globally
unique. Persistent overlays StreamingAssets while retaining fallback chunk
resolution. Missing dependencies, ambiguous external targets, malformed
objects, and unsupported schemas must remain explicit.

### Three exported types carry no provenance, and it costs their references

The rule above is a rule about the export's *output*, and the output does not
keep it everywhere. Of the JSON-bearing exported types:

| provenance | types |
| --- | --- |
| an `$animestudio` block with `sourceFile` | MonoBehaviour, PlayableDirector, AnimatorController |
| the same fields at top level instead | Animator |
| **none at all** | **Material, TextAsset, AnimatorOverrideController** |

The last row has a consequence rather than being a tidiness complaint.
Resolving a cross-file `PPtr` needs the *referrer's* container, because
`m_FileID` indexes that container's dependency list (see
[`containers_cabmap.md`](containers_cabmap.md)). A Material does not record
which container it came from, so the rule cannot be applied to it at all.
`Material.m_SavedProperties.m_TexEnvs[*].m_Texture` holds 243,124 non-null
references across the 66,906 materials and **97.7% of them are cross-file**,
so the published material-to-texture links rest on matching a PathID globally
with no way to notice being wrong. They are probably right -- PathIDs are
measured unique across this export -- but "probably right and uncheckable" is
the state this lane exists to avoid, and it is the state the evidence rule
above forbids.

Two things follow. The fix belongs in the exporter, not in a builder: emit for
these three what the other four already carry. And the name half of the
existing link is not a second opinion -- `m_Texture.Name` is empty in every
material in the export, so the name-first branch in
`scripts/webui/assets/index.py` never fires and the PathID is doing all the
work alone.

**The fork now emits it, and the export has not been rebuilt.** `ExportJSONFile`
handled `MonoScript` and the generic `Object` case and fell through for every
*typed* asset class, which serialized straight to Newtonsoft with no wrapper.
The typed branch now converts through `JObject` and inserts `$animestudio`
first, so the asset's own serialized shape and member order are unchanged.
Validated on a bounded single-chunk dump of 7,488 materials: 7,482 are
byte-identical to the current export once the new block is removed, and the
other six differ **only** in `m_FileID` values, never in a PathID or any other
leaf.

Those six are the confirmation, not the exception. They are the same objects
read from a *different* container, and a container orders its own externals
list, so the identical target PathID sits at a different slot -- `m_Shader`
at 39 here and 42 there. That is the whole reason the provenance matters: a
`m_FileID` is meaningless without knowing which container is doing the
referring.

Two cautions before this reaches a build. The shipped
`bin/Release/net9.0-windows` CLI is deliberately **not** rebuilt here: the
corpus gates' `inputSetSha256` covers the CLI binary, so rebuilding it
invalidates that audit, every gate below it and the contracts pinning it, and
that should be a deliberate act rather than a side effect. And the export must
be re-run before any consumer sees the new field, so a builder reading it must
tolerate its absence.

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
<export root>/meta/<Layer>/asset_status/
<export root>/meta/<Layer>/export_manifest/
<export root>/meta/extraction/failures/
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
- Rebuild the CLI and re-export so the new Material/TextAsset/
  AnimatorOverrideController provenance actually reaches consumers, then
  re-run the corpus gates, whose `inputSetSha256` the rebuild invalidates. The
  fork change is written and validated on a bounded dump; nothing downstream
  sees it yet.
- Recover more exact MonoBehaviour and managed-reference schemas. The
  `m_RefTypes` upgrade above closed every non-empty undecoded managed-
  reference payload in the slice it was measured on; what remains is the
  hand-written decoders it did not need to replace, and any type whose
  RefTypes entry is absent or not unique.
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
