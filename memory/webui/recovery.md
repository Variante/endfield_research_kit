# Recovery page recovery

## Purpose

Recovery shows how far the installed game data is understood, in two parts: a
log-scaled VFS block-volume bar, and a tree of VFS blocks whose leaves are the
logical-file types (declared path families) with their L1–L4 recovery state.
The four levels are defined in [`../game_data/README.md`](../game_data/README.md).

Its reason to exist is evidence honesty. Open and unassessed levels are shown
with the same prominence as closed ones, and "framed and named" stays apart
from "understood": a stage is a scoped state, never a percentage.

## Inputs and recovery flow

The builder never re-decodes bytes and never reads the installed client.

1. `reports/animestudio/vfs_payload_profile_files_latest.jsonl.gz` supplies one
   row per declared logical file: raw VFS block id and exporter name, virtual
   path, chunk name, declared size, bytes read, and profiler status. Block and
   family tallies are measured from these rows; the profile's coarse
   `pathFamily` does not decide a family.
2. `scripts/webui/recovery/recovery_declarations.json` supplies the reviewed
   enum-id/exporter-name pairs, lane per block, family path patterns, the
   bilingual per-level stage statements with cited sources, the stage-state
   vocabulary, and the recorded evidence limits a stage may cite. The C# enum
   remains the authority for the block list; a focused test compares it.
3. `memory/game_data/README.md` supplies the four level names and questions
   (the `## The four levels` table), parsed rather than copied.
4. The export's AnimeStudio asset maps (`meta/<Layer>/asset_map/`) supply one
   entry per mapped Unity object: source chunk, PathID and type. The export's
   own VFS index (`meta/<Layer>/vfs_index/`) assigns each chunk to its block,
   so a chunk added by a client update after the payload profile still
   resolves. Layers are read Persistent first and an object is keyed by
   (type, PathID), so a bundle Persistent replaces is counted once. The
   declarations' `unityObjectTypes` give each type its four stages; a family
   opts in with `objectTypes: true`.

Every input is fail-closed: a missing file, unexpected `schema`, malformed
profile row, unknown raw block id or changed exporter name, a level table that
is not 1..4, an ambiguous family pattern, a stage citing a missing source or an
unknown evidence limit, a level stronger than the one below it, or level 4
declared `closed` all abort the build, as do a missing asset map or VFS index
and an asset-map chunk no VFS index assigns to a declared block. A path matching no declared family is
kept as `Other / unclassified` with all four levels `notAssessed`; so is an
asset-map type with no declaration.

## Primary generated outputs

```text
webui/data/recovery/index.json
```

One compact v5 payload: `levels`, `stageStates`, `lanes` (id and label),
`evidenceLimits`, `sources`, and `vfs` with `totals` and `blocks[]`. Each
block carries its measured tally and its `families[]`; each family carries its
measured tally with sample paths, its path pattern, and four declared stages;
the Unity bundle family also carries `objectTypes[]`, each with a measured
object count and four declared stages. Chunk names are counted
(`containerChunks`) but not listed.

## Evidence boundary

- **Measured**: file counts, declared/profiled bytes, container-chunk counts
  and availability, all from the VFS profile. `profiledBytes` counts only
  `profiled` rows whose declared bytes were fully read. Absent rows
  (English/Japanese/Korean audio and AuditAudio chunks are cataloged but not
  installed) never contribute local payload. Unknown statuses fail the build.
- **Declared**: family patterns and stages, each stage citing its memory topic.
  `closed` means the stated boundary is closed, `partial` that only selected
  records or fields are, and `open`/`notAssessed` keep the gap visible. No
  family can claim L4 closed. A stage is not a fraction of files or bytes.
- IFix patch L3 names the current opcodes and selected operand routes through
  authenticated file-VM code, including frame slots, exception records, and
  uniquely resolved external signatures. Its L4 identifies declared fix
  targets and conditional VM invoker flow only. A patch load, dispatch, and
  resulting behavior still lack a runtime receipt; both stages remain partial.
- DynamicStreaming `fb_version.bytes` has its own stages. The authenticated
  current corpus closes its version-root framing, and selected native accessors
  name the root and entry fields. The same-scene IdComp join and the native
  version-ban route support only a partial L4 reading: the route has build and
  branch guards, and the page makes no claim about a live phase, selected
  file, or ban result.
- DynamicStreaming `fb_init` and `fb_streaming` now have partial L3/L4 stages.
  The selected route stores their paths separately, requests two streams,
  and resolves their ready buffers to separate FlatBuffer roots. At the same
  ordinal, a selected consumer passes the second-root field-six row's ID vector
  and first-root field-seven row's descriptors and nested blob to a native
  builder. Its signed ID/stride loop copies count-times-stride byte segments;
  the authenticated pair corpus independently confirms exact blob tiling.
  Descriptor meanings, chosen VFS files, and live activation remain open.
- IV room files now have a partial L4 stage. The selected ready-buffer handler
  checks their magic, reads the stored header structure and copies grid-cell
  count times 8 or 16 bytes; the current files fit the 16-byte branch. The
  path builder appends a formatted room name to the supplied root directory.
  The copied allocation reaches a callback, command binding, and virtual
  dispatch request sized by cell count. The two finite triples have only an
  inferred bounds role, and record fields, live root value, selected file,
  GPU execution and texture format remain open.
- Terrain `LAYER_C/D/N` now has partial L4 stages. Selected native paths
  conditionally carry the grouped path-result handles to owner-local resources
  bound to `_ConeMaps`, `_Splats`, and `_Normals`, respectively. This replaces
  the former page claim that no `LAYER_C` consumer was identified. The named
  render-property route does not identify stored pixel channels, managed
  `VirtualTextureRenderer` fields, shader sampling, or which installed file a
  live scene selected.
- Bar widths use `log10(1 + 100 × value / smallest nonzero value)` normalized
  across segments so every observed block stays visible; tooltips give the
  untransformed value and true share. The bar describes inventory, never
  recovery coverage.
- Object counts cover only the types AnimeStudio's asset map lists; GameObject,
  Transform, renderer components and other unmapped types do not appear, so the
  counts are not a full census of a bundle's objects. The asset-map scan adds
  about a minute to the build.
- Evidence limits (`evidenceLimits`) record a disconfirmed route or a runtime
  observation gap, not a completion queue; they do not rule out future static
  evidence.
- Reports under `reports/` are local-only; `sources` records each input's size
  and mtime, and the page shows an explicit missing or schema-mismatch state
  when `index.json` is absent or not v5.

## Focused refresh

```bat
python -m scripts.webui.recovery.build_recovery
python -m scripts.webui.recovery.build_recovery --print-summary
python -m unittest scripts.tests.test_build_recovery
```

The page is reached at `#recovery` (tab `Progress` / `进度`). It is debug-only:
the tab carries `data-debug-view="1"` and `hidden` in `index.html`, `assets.js`
lists `recovery` in `DEBUG_ONLY_VIEWS` with a `story` fallback, and it appears
once `Show debug info` is on. It is not part of `export.bat`: its input is a
focused profile report with its own refresh command.

## Highest-value remaining gaps

- No level-4 coverage measurement exists. Stage statements are scoped
  interpretations of durable topics, not counts of understood bytes; a coverage
  measure needs per-family, consumer-proven evidence.
- Cross-block measurements are no longer shown here: JsonData named-byte
  coverage belongs to [`../game_data/serialization_memorypack.md`](../game_data/serialization_memorypack.md)
  and the MonoBehaviour field/table-key evidence to
  [`../game_data/unity_assets.md`](../game_data/unity_assets.md). A family's L3
  stage should cite those topics rather than restate their numbers.
- The block-type-to-lane map is a declaration that must be revisited whenever
  the VFS enum changes; the builder fails closed to force that.
- BundleManifest has exact partial framing in
  [`../game_data/extraction_payload_boundaries.md`](../game_data/extraction_payload_boundaries.md),
  while its field ownership and value semantics remain open.
