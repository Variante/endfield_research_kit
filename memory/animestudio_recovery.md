# AnimeStudio recovery

AnimeStudio is the maintained extraction boundary between installed Endfield
data and the repository's builders. Production users should enter through the
root wrappers; direct CLI commands are for focused recovery and diagnostics.

## Ownership

| Layer | Owner |
| --- | --- |
| Installed VFS catalog, overlay, block reads, Unity objects, conversion | `tools/AnimeStudio/` |
| Installed-game orchestration, scope, worker isolation, provenance | `scripts/export_full_from_game.py` |
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
| Apply a local client delta without publishing Updates | `.\export.bat --changed-only` | changed focused VFS files, full bundle-derived refresh, all WebUI builders |
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
[`webui_recovery.md`](webui_recovery.md) for the complete publication flow.

## Build and direct CLI use

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Expected executable:

```text
tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe
```

Use direct `dump`, `audio`, `stream`, `vfs-index`, or `list` only for a bounded
probe. Inspect each subcommand's `--help`; do not maintain another option
catalog here. `dump`, `audio`, `stream`, and `vfs-index` support the sibling
root fallback. `dump`, `stream`, and `vfs-index` support repeated block-type and
file-regex filters. Audio defaults to direct lossless FLAC.

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

## VFS and payload recovery

The outer VFS boundary and each inner payload schema are separate claims. A
validated range/hash proves the bytes under study, not their fields or runtime
meaning. Start at the VFS recovery evidence index in the AnimeStudio skill
reference; it maps each active family to its maintained reader, fixtures,
corpus report, and remaining boundary.

A parser becomes exact only after positive fixtures, truncated/malformed/
trailing-byte negatives, exact-consumption checks, and a current-corpus sweep.
Keep authored field names, envelope framing, cross-file ownership, and observed
runtime behavior as separate evidence layers. Changing totals and source
fingerprints belong in generated reports.

Current durable boundaries:

- Bundle and InitBundle nested-container framing, current VFS logical-file
  reads, Terrain and Streaming envelopes, all five DynamicStreaming root
  families, LipSync payloads, video outer framing, and several routed JsonData
  families have fail-closed readers.
- The current Table corpus has a direct low-output sweep covering selected
  overlay provenance, decoded MD5, exact read length, SparkBuffer parsing, and
  EOF for every metadata declaration. BundleManifest and IFixPatchOut likewise
  have current exact framing sweeps. BundleManifest additionally has exact
  inner-file-count, basename-multiplicity, and row-index witnesses, but no
  serialized field ownership; stale AssetMap source chunks cannot supply it.
  Exact method pins exist, but unresolved stream/ref-out carriers still block a
  safe lookup capture ABI. IFix instruction/runtime meanings remain separate
  claims.
- Irradiance-volume region framing is exact for seven files; all 92 IV indexes
  have a bounded unique UTF-16LE filename-table parser that references the 138
  remaining payloads exactly once. Those payload records and renderer meanings
  remain unresolved.
- IV runtime capture has a narrow UnityPlayer parser/cursor candidate, but must
  still close exact module/build/entry/caller, buffer-length, and final-cursor
  contracts. A generic file-I/O hook cannot preserve the authenticated virtual-
  path/hash join, and a stale capture manifest must fail preflight before the
  game starts. The current native parsers have no payload-length parameter or
  final EOF check, and repeated in-payload magic values rule out signature
  scanning as a replacement boundary witness.
- Audio has fail-closed AKPK/BNK/DIDX/DATA/media framing and a direct audit;
  HIRC behavior, selected runtime playback, and audibility remain separate.
- SkillData and BuffData have current exact-build member-count and file-hash
  censuses, but nested MemoryPack unions and whole-file EOF consumption are not
  proven. BuffData remains blocked on an untyped ability-event union and an
  unresolved modifier interval. LevelScriptData candidate tails do not consume
  the preceding top-level object/action map. Keep these families unclassified
  until formatter IL or a bounded deserialization trace closes the cursor.
  Current v29 metadata identifies formatter/wrapper methods and setters, but
  its missing generic mapping and mismatched native code-registration witness
  do not prove serialized field order. The current residual JsonData census
  keeps 9,388 outer-verified rows across 14 families explicitly unclassified;
  SkillData is the largest by bytes and still lacks whole-object cursor proof.
- Deeper Terrain, streaming, manifest-row, mmap-oriented string/hash and bone
  data, patch-instruction/runtime, and remaining JsonData semantics are
  incomplete.
- Material and shader extraction preserves recoverable metadata; it does not
  prove renderer ownership, selected variants, final lighting, or appearance.

## DummyDll and MonoBehaviour schemas

```bat
python -m scripts.animestudio.generate_dummydll --dry-run
python -m scripts.animestudio.generate_dummydll --replace
```

DummyDll generation is tied to the exact installed `GameAssembly.dll` and
`global-metadata.dat`. The generator must uniquely recover registrations,
validate a complete staged managed image set, publish atomically, preserve the
previous set, and record provenance in `tools/DummyDll/generation.json`. Never
reuse registration addresses from another build.

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

- Complete inner semantics for the unresolved VFS payload families.
- Improve per-object clean/partial/error certification and dependency diagnostics.
- Recover more exact MonoBehaviour and managed-reference schemas.
- Expand shader-container coverage and complete semantic shader fixtures.
- Add converter regressions for more Unity layouts.
- Reduce peak memory for broad Story JSON/object-index work without unsafe
  filtering or unsupported JSON concurrency.
