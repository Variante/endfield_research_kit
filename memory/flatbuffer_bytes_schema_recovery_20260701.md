# FlatBuffer streaming `.bytes` schema recovery — 2026-07-01

P5 of `memory/improvement_plan_20260701.md`. Moves the world-streaming `.bytes`
population from "identified as FlatBuffer-like" to clustered root-table shapes
with one family bounded with named offsets and two population-scale exact
checks. All labels below are evidence with sample counts unless marked exact;
no field names are invented.

Tooling: `scratch/flatbuffer_bytes_recovery/` (`fb_reader.py` conservative
reader, `scan_clusters.py` census, `deep_dive.py` recursive bounded parser,
`verify_chunk_root.py` full-population hypothesis checks, `make_report.py`).
Generated evidence: `tmp/flatbuffer_bytes_clusters_20260701.md` / `.json` plus
the per-run scan/deepdive/rootcheck JSONs in `tmp/`.

## Census (exact)

- `export_full/structured/StreamingAssets`: 38,824 `.bytes`; 38,561 validate as
  FlatBuffer roots (strict root-uoffset/vtable/field-offset invariants); all
  263 rejects are `Data/IrradianceVolume/PC/**` custom payloads.
- `export_full/structured/Persistent` mirrors the same tree (38,826 files; the
  2 extra are `Data/IFixPatchOut/Windows`, non-FlatBuffer). A 64-file random
  sha256 sample found 63 byte-identical and exactly one differing same-size
  file: `Data/DynamicStreaming/PC/Scene/indie_ccdg001/fb_main_5_0001_0002.bytes`
  (Persistent copy likely patched — worth a full-tree hash diff if Persistent
  deltas ever matter).
- The 38,561 valid files fall into exactly 5 root vtable signatures:

| signature | files | families |
|---|---|---|
| `vt20/obj40/off[4,8,16,20,24,28,32,36]` | 38,064 | InitChunkData x18,277 + Global x83; StreamingChunkData x18,277 + Global x83; fb_init x672; fb_streaming x672 |
| `vt14/obj28/off[16,12,24,4,8]` | 202 | fb_main variant A |
| `vt14/obj32/off[16,12,28,4,8]` | 162 | fb_main variant B |
| `vt10/obj16/off[4,8,12]` | 68 | StreamingChunkInfo (one per scene) |
| `vt18/obj52/off[4,12,8,28,24,16,20]` | 65 | FBStreamArea |

Static (`Streaming/PC/<scene>/`) and dynamic (`DynamicStreaming/PC/`) chunk
files share one root shape — one writer, one schema family.

## Chunk-manifest root (the 38,064-file cluster), named offsets

Deep dive: 3,085 files sampled across every filename family, full recursive
bounded parse, 0 parse failures; root checks ran on all 38,064 files.

- slot0 @ +4: int32 == 46 in 38,064/38,064 (exact constant; meaning unproven,
  version/format candidate).
- slot1 @ +8: inline 8-byte int32 pair (vtable hole at +12). **Exact join:**
  equals filename coordinates x128 in 36,554/36,554 coordinate-named
  `*ChunkData_x_y_*_*` files, 0 mismatches — chunk world-origin with 128-unit
  chunk pitch (evidence label). `_Global_`/`fb_*` files do not satisfy it.
- slot2 @ +16: vector<table> (env-object records `vt16/obj44/off[4,0,0,8,16,40]`
  and relatives) or empty.
- slot3 @ +20, slot4 @ +24: vectors, element type unproven (scalar/struct),
  len up to 52,549. Parallel-array hypothesis (3/4/5 equal lengths) FAILED at
  population scale — dropped.
- slot5 @ +28: vector<table> of named-object records in 3,085/3,085 samples.
- slot6 @ +32: vector, mostly empty; else single-slot wrapper `vt6/obj8`.
- slot7 @ +36: byte-ambiguous empty-string/empty-vector in most files; in
  `_Global_` files a vector of tables referencing object-name strings.

Named-object record `vt16/obj44/off[4,8,12,16,20,40]` (12,851 sampled; sibling
`vt16/obj40/...` 9,870): slot0 = name string 12,851/12,851 (Unity
`<name>#<n>_<hex>` convention, same as envEmoji notes); slot1 = small enum 1..7
(5 dominant); slot2 = usually string (often empty); slot3 = table
`vt16/obj16/off[0,0,0,12,8,4]` (transform candidate, unproven); slot4 = scalar,
f32-plausible 0.991, dominant 0 with bitmask-like outliers; slot5 = vector,
mostly empty.

Content classes seen in names: colliders (`P_*_COL1`, `S_tree_*_COL1_UM01`,
`BattleShape`), merged renderables (`*_ECSMerged`), lighting (`Global Env`,
`Directional Light`, `Reflection Probe(s)`, `Linear Light` via
`vt14/obj28|24/off[4,8,0,16,12]` group->children), audio placement
(`AudioEmitter_*`, `AudioBox_*`, `SOCChunk_*` via `vt12/obj20`),
terrain/surface (`SurfaceTypeData_x_y`, `ClothGroupInfo_*`, `TerrainRoot` via
`vt12/obj16`).

## Semantic joins

- slot1 == filename coords x128: exact, 36,554 files.
- `_Global_` InitChunkData embeds `Assets/Beyond/DynamicAssets/Scenes/PC/<scene>/Terrain`
  and `Data/IrradianceVolume/PC/<scene>` — direct join from streaming to the
  IrradianceVolume family (the 263 non-FlatBuffer rejects).
- `P_*` model/effect family names in 990/3,085 sampled files (`P_rock_map01_*`,
  `P_build_com_tower*`, ...) — joinable to ModelTable/prefab families.
- fb_main child tables (`vt114/obj24`, 55 slots, ~50 always absent) hold
  prefab paths (`Assets/Beyond/Arts/Effects/Map/prefab/**/P_fxmap_*.prefab`),
  bundle-style foliage paths (`assets/beyond/arts/gameplay/interactive/foliage/partial/p_itree_*`),
  and interactive ids (`int_P_prop_com_machine`) — dynamic-decoration bindings.
- Negative result: no `dlg_*`, `eny_*`, `chr_*`, `npc_*`, `sc_*` ids anywhere in
  the sampled cluster. This population is scene geometry/lighting/audio
  streaming, not story/spawner data — do not mine it for story order.

## Small clusters

- `StreamingChunkInfo` (`vt10/obj16`): 3 vectors; slot2 = vector<table
  `vt10/obj20/off[4,12,16]`> len 4..7,222 — per-scene chunk registry; child
  slot0 is an 8-byte inline pair (chunk-coordinate candidate, unproven).
- `FBStreamArea` (`vt18/obj52`): 4 short vectors + a 24-byte inline block at
  +28 that is f32-plausible 1.0 with observed +/-100000.0 — six-float
  bounding-box candidate, unproven.

## Known ambiguities (fail-closed)

- Empty string vs empty vector is byte-identical; reported ambiguous.
- Scalars can decode as valid forward uoffsets, producing false string/vector
  hits; the mixed kind ratios in the report expose this instead of hiding it.
- Vector element widths for scalar/struct vectors are unrecoverable without
  schema; left `unproven-scalar-or-struct`.

## Recommended next steps

1. Search IL2CPP metadata/GameAssembly for the FlatBuffers accessor classes
   (`InitChunkData`, `StreamingChunkData`, `FBStreamArea`, `SOCChunk`,
   `ClothGroupInfo`, `SurfaceTypeData` are strong string anchors) to recover
   real field names for the 8 root slots — same approach that recovered the
   MemoryPack setter orders.
2. If names land, promote a bounded typed reader for slot1 (chunk origin) and
   slot5 (named-object records) into the Data-index FlatBuffer preview,
   replacing `fieldN` labels for this cluster only.
3. Full-tree hash diff StreamingAssets vs Persistent `.bytes` if patched
   Persistent copies become relevant (one same-size differing fb_main found).
4. Struct element widths in slots 3/4 could be pinned by allocation-adjacency
   analysis (vectors packed back-to-back) — only worth it after step 1 fails.

## 2026-07-02 Review Caveats

An independent code review approved the reader with nits. The validator is
fail-closed (bounds, parity, forward-only uoffsets, strict strings); malformed
files are never force-parsed. Evidence-quality caveats:

- `DeepDive.probe_vector` always returns `True`, so `classify_slot`'s child
  table branch is effectively dead: real child tables reached directly from a
  root slot are systematically labeled `unproven-scalar-or-struct` vectors and
  not walked. The two population-scale proofs (slot0 == 46, slot1 == filename
  coords x128) are unaffected, but per-slot table/vector labels in the deep
  dive report are skewed and should be re-derived after fixing the probe.
- Prefix-bounded scans (8 KiB) can mark a valid file `bad-root-vtable` if the
  vtable lies beyond the prefix — conservative direction, irrelevant for the
  observed root offsets, but census counts depend on it.
- Field-offset check allows a 4-byte slot to extend past the object end by up
  to 3 bytes; tighten to `off <= object_len - 4` for offset-follow paths.

Fixing `probe_vector` and re-running the deep dive is the first step before
IL2CPP accessor-name recovery, so slot classifications stand on real evidence.

## 2026-07-02 probe_vector Fix and Corrected Deep Dive

Fixed the review finding: `DeepDive.probe_vector` now returns True only for
proven element kinds (all-table, all-string, or empty — a table is impossible
at a zero word because soffset 0 is rejected). `classify_slot` now prefers a
verified child-table layout over the unproven-vector hypothesis and labels the
fallback as `vector-unproven`. Also fixed family sampling to re-normalize
candidate names (digits -> "N") instead of reversing "N" -> "*", which
corrupted globs for filenames containing a literal N.

Corrected deep dive (`tmp/flatbuffer_bytes_deepdive_20260702_fixed.json`,
same 3,085-file sample, 0 failures) vs the original run:

- Root slots 2/5/6/7 are unchanged — the proven vector-of-table and
  vector-of-string claims (named-object records, string slots) were real.
- Root slots 3/4, previously labeled `vector` in ~3,084 files each, are now
  honestly `vector-unproven` (3,073 / 3,082) — schema-less evidence cannot
  distinguish them from scalar/struct data.
- The fix uncovered previously shadowed real child tables: 11 at slot 3, 3 at
  slot 4, and slot 1 tables rose from 22 to 32. Three new table signatures
  appeared, led by `vt6/obj20/off[0]` (12 instances).
- Caution: the new single-instance `vt42/obj62682/off[...]` signature has very
  large field offsets and may be a false table layout admitted by the loose
  `off <= object_len - 1` slot-width check; treat as suspect evidence until
  the fb_reader check is tightened to `off <= object_len - 4`.

The original `tmp/flatbuffer_bytes_deepdive_20260701.json` and the narrative
report's per-slot table/vector labels are superseded by the fixed run for
slots 1/3/4; population-scale invariants (slot0 == 46, slot1 == filename
coords x128) were never affected.
