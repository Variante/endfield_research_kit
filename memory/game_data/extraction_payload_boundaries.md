# How far each reader is proven

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, extraction lane.** One statement per payload family: which reader is
fail-closed, how far its framing is exact, and where it stops. This is the
*boundary* layer -- what the data inside a family means belongs to that family's
lane file, and a reader boundary here never implies a semantic there. Reader
mechanics (member orders, cursor rules, framing quirks) live in the named
module's docstring and its contract under `scripts/game_data/contracts/`.

## What "proven" means

- The outer VFS boundary and each inner payload schema are separate claims. A
  validated range and hash proves the bytes, not their fields or runtime
  meaning. The VFS recovery evidence index in the AnimeStudio skill reference
  ([`animestudio.md`](../../.codex/skills/animestudio-workflow/references/animestudio.md))
  maps each family to its reader, fixtures and corpus report.
- A parser is exact only after positive fixtures, truncated/malformed/
  trailing-byte negatives, exact-consumption checks and a current-corpus sweep.
  Authored field names, envelope framing, cross-file ownership and observed
  runtime behavior stay separate evidence layers.
- EOF closure is necessary, not sufficient. A same-width wrong reading also
  closes (the SpawnerConfig `Optional<Vector3>` case in `spawner_binary`), so a
  framing conclusion needs a second signal: a boundary on a known marker, a
  coherent value distribution, or a closed field domain.
- Exact closure of a child never promotes its parent, and a named stored field
  is not its runtime consumer or effective value.
- Freshness is live provenance, not a report digest: consumers recheck
  catalog, build, CLI, parser and chunk fingerprints at both ends and
  reauthenticate with a rebuilt tool instead of rewriting pins. Each MemoryPack
  family report pins only its own gate's import closure. DummyDll population
  never fills a missing native proof. Totals and per-file rows stay in reports.

## The JsonData registry

`scripts.game_data.jsondata_corpus` joins every current JsonData identity to
the export by safe path, length and logical MD5, runs only maintained readers,
and records one terminal state per file; its docstring defines the states. A
path, extension or leading member count never supplies a schema. BuffData and
SkillData enter through their family reports, which own formatter, cursor,
native-input and semantic claims. A complete registry is an accounting result:
consumers gate on the per-file state, and whole-schema recovery stays a
per-family claim.

## Per-family boundaries

### Containers, catalogs and code

| Family | Reader / gate | Boundary | Stops at |
| --- | --- | --- | --- |
| Bundle, InitBundle | AnimeStudio nested-container readers | fail-closed nested container framing over current VFS logical-file reads | object identity: [`unity_assets.md`](unity_assets.md) |
| Table (`TableCfg`) | direct AnimeStudio full-block dump | every metadata declaration: overlay provenance, decoded MD5, exact read length, SparkBuffer parse, EOF; JSON byte-equal to the structured export | field meaning (text consumers) |
| BundleManifest | `bundle_manifest`, `bundle_manifest_corpus`, `bundle_manifest_native` | exact: Brotli envelope, two headers, two capacity-sized hash-slot/value dictionaries, the 48-byte indexed Bundle array, the sequential UTF-16LE record span, the Brotli AssetInfo path suffix, EOF. Native reads name every AssetInfo and Bundle field; `hashName`, `pathHashHead` and every `hashVersion` replay | live lookup, unseen-name case handling, Unity object ownership |
| Bundle dependency graph | `bundle_cab_dependency_corpus`, `bundle_cab_exceptions`, `bundle_external_identity_corpus` | stored graph: reverse list is the direct graph's inverse, `dependencies` its transitive closure, projected CAB externals a sub-multiset of the direct list; the loader's direct-list recursion is a static consumer | authoring of a small manifest-only residual, one CAB-shaped external's target, load order |
| IFixPatchOut | `ifix_patch`, `ifix_vm_*_native` | exact current method spans; selected `Instruction`/`Code` name every opcode; call, branch, `Ldstr` and field operands join file tables | reflection selection, remaining operands, patch activation: [`ifix_patch.md`](ifix_patch.md) |
| StringPathHash (main, initial) | `extend_data_binary`, `string_path_hash_corpus`, `string_path_hash_native` | both dictionaries self-bound lookup and value pools; every pair replays against VFS filename hashes or manifest AssetInfo | catalog writer, runtime lookup |
| FacBoneTRS | `extend_data_binary` | file-provided unit count, contiguous bone records, 64-byte ranges through EOF; every value shape-consistent with a row-vector rigid-affine 4x4 float matrix | exact type/convention; unit and bone hashes match neither StringPathHash catalog |
| CompressData | AnimeStudio `EndfieldCompressData`, `extend_data_compress_corpus` | count, offset table, Brotli UTF-16LE JSON bodies, EOF; reviewed NodeCanvas root and task-envelope schemas | nested task values, blackboards, execution: [`extend_data.md`](extend_data.md) |
| Video (`.usm`) | AnimeStudio video reader | fail-closed outer framing; inner streams go to the decoder | narrative attachment, playback |
| Wwise packages, hotfix | AKPK/BNK/DIDX/DATA readers | fail-closed; hotfix packages use the same package reader; SDK-backed readers frame music bodies `0x0A`-`0x0D` exactly although the built-in HIRC dispatcher skips them unless a hook is registered | HIRC behavior, playback: [`audio_overview.md`](audio_overview.md) |
| Material, Shader | AnimeStudio export | recoverable metadata preserved | renderer ownership, selected variants, final lighting |

Audio availability is data-driven: shared and language blocks parse whenever
any declared chunk exists; a block absent from both overlay roots is a visible
conditional missing state, while partial presence, bad hashes and malformed
payloads fail closed.

### World blocks

| Family | Reader / gate | Boundary | Stops at |
| --- | --- | --- | --- |
| Terrain tiles (TRET, `_H`) | `terrain.tret`, `terrain.height` | raw or length-prefixed inverted-LZ4 envelope, versioned TRET prefix, body-length word equal to the decoded payload; `_H` row-major height samples | height scale, no-data, channel meaning: [`world_terrain.md`](world_terrain.md) |
| Terrain `LAYER_D`/`LAYER_N` | `terrain.tret`, `terrain.native`, `terrain.corpus` | offset 14 is a direct `GraphicsFormat` selector (108/109: BC7 sRGB/UNorm, 16 bytes per 4x4 block); bodies split into exact contiguous mip-like ranges and consume EOF; unobserved header tuples fail closed | offset 12 as mip count is inferred; block contents, texture-array ownership, rendering |
| IV index | `irradiance_volume` | bounded unique UTF-16LE filename table and one uniquely located directory (absolute or table-end-relative alignment); legacy indexes use a separate EOF-ending directory | -- |
| IV payload | `irradiance_volume`, `irradiance_volume_corpus` | index-directed ranges tile every referenced payload through EOF | record fields; the native parser takes no length and checks no EOF, and repeated in-payload magic rules out signature scanning: [`world_irradiance.md`](world_irradiance.md) |
| StreamingChunkInfo | `streaming.framing` | exact anonymous table/vector graph in every current file (reused and forward vtables, 4/8/12-byte widths); every nonzero byte owned | field names; catalog projection in [`install_and_vfs.md`](install_and_vfs.md) |
| InitChunkData, StreamingChunkData | `streaming.framing`, `streaming.corpus`, `streaming.native` | three exact anonymous subgraphs: root field 2 through EOF, parallel fields 3/4/5, paired fields 6/7. Streaming field-2 rows close against seven selected layouts; native gates read row fields 0-5 as scalar32 x3, int32[2], float32[6] and a scalar32 hash-key vector | names, key namespace and signedness, the runtime root's logical file; bytes outside the subgraphs |
| DynamicStreaming `fb_main_*` | `dynamic_streaming`, `dynamic_main_native` | field-specific `SingleGrid` vector widths bound bodies without overlap | whole-file and nested-record closure: [`world_dynamic_streaming.md`](world_dynamic_streaming.md) |
| `FBStreamArea` | `dynamic_stream_area_corpus` | with `RootVisible` and `AreaVisibleGroups` as `Int32`, six vector count words and bodies tile the tail from root end to EOF | record meaning (world lane) |
| `fb_init`, `fb_streaming`, `fb_version` | `dynamic_streaming`, `dynamic_aux_pair_corpus` | see [`install_and_vfs.md`](install_and_vfs.md) | descriptor meanings, live selection |

Streaming nested targets stay anonymous and conditional on their `streaming/`
gates (conclusions in the `world_chunk_*.md` files):

- **Marker 17**: two wrappers and a counted byte range; `streaming.marker17`
  refines native-selected tag5 bodies (64-byte header, one optional record,
  five counted arrays) and fixed tag1/4/6 profiles. Body EOF is a parser
  requirement, not a native check; tag6 must not be dispatched as tag1.
- **Marker 15**: nonzero forward bounded targets only; exact 16-byte physical
  gaps in selected scenes bound those addresses, not a record width or owner.
- **Marker 13** (selector 9, key `FF000000`): a 16- or 18-byte physical gap
  between certified ranges, four scalar32 positions consumed conditionally.
  **Marker 2** (selector 6, key `09020000`): a 4- or 6-byte gap, four bytes
  projected. The rest stays opaque even when zero; marker-2 selector 9 and
  multi-target clusters stay unsupported.
- **Pairs** (`streaming.pairs`): Init first, Streaming second, one serialized
  ordinal; ordered field-3/4 vectors match, row field 0 is not shared identity.
- **Filename relations** (structural, not coordinates): in numeric files the
  field-2 row field-3 lanes floor-divided by 128 equal the first two filename
  integers (residuals 0/32/64/96) and present fields 1/2 equal the last two;
  `Global` files have a separate field-1/2 relation.
- The native read closes requested/returned length and root resolution, then
  is pointer-only (no parsed length or final cursor). Marker associations are
  not a union registry; marker 16 is a different outer-row shape.

### JsonData families

| Family | Reader | Current boundary | Stops at |
| --- | --- | --- | --- |
| LipSync | `memorypack.lipsync`, `memorypack.lipsync_corpus` | strict 15-member reader through EOF on every file; rows are native-proven Unity `Keyframe` values | playback selection |
| NPC MontageNew | `memorypack.npc_montage`, `memorypack.npc_montage_corpus` | complete named schema through EOF (3-member root, 24-member body, nested records) | runtime selection, playback |
| NPC PrefabInfo, catalogs | `schemas.npc_prefab_info`, `schemas.npc_catalog` | exact JSON schemas; extra or reordered fields refused | consumers |
| MissionRuntimeAsset | `schemas.mission_runtime_main`, `schemas.mission_runtime_meta` | exact JSON schemas | Story semantics: [`../webui/story_recovery.md`](../webui/story_recovery.md) |
| MapConfig, UILevelMapLoadConfig, textual roots, LevelMountPoint, compact GameplayConfig JSON | `schemas.*` | exact named JSON schemas | consumers |
| LevelData | `leveldata_binary`, `leveldata_bezier_knot_corpus` | complete 43-field named schema through EOF on every current file, spline knots as raw 56-byte values; an unsupported future nested body stops at its field | runtime selection (which point, which patrol); knots are local to each row's transform (`leveldata_spline_runtime_native`: `direct` for the normal branch, `conditional` at runtime) |
| LevelScriptData | `levelscript_binary` sequential owners | most files close a complete named schema at EOF; the residue is bounded partial, keeping an action-map named prefix or the five-member terminal suffix, stopped at its first unsupported action-map union route | per-route codecs (recovery order below) |
| LevelScriptTemplateData | `levelscript_template_binary` | part of the family closes named exact; the rest is bounded partial at a recorded action-map refusal | same union-route work |
| SkillData | `memorypack.skill_corpus` | most files whole-schema exact through native-gated readers and replayed live cursor receipts; the residue keeps a named prefix and an authenticated terminal | distinct unsupported nested action tags; provider/cache selection |
| BuffData | `memorypack.buff_corpus`, `memorypack.buff` | every file has a named 30-field outer frame through EOF; a native-gated subset (no-positive, positive-damage, sole CreateBuffAction roots) is whole-schema exact | interior action and icon bodies of the rest |
| Interactive | `interactive_binary`, `memorypack.interactive` | every current table, template and ModelViewStateController file exact | future variants fail closed |
| SpawnerConfig | `spawner_binary` | generated five-field cursor through EOF on every file | positive route-action lists (absent; fail closed) |
| AnimationConfig, CharInteractPerformCfgs, AtmosphericNpcData | `animation_config_binary`, `char_interact_perform_binary`, `atmospheric_npc_binary` | exact on every current file | runtime selection and use (stored, authored data only) |
| GPUISystemConfig | `gpu_ui_binary` | ExtendedPrefabGroup roots and DamageText close complete named schemas | prefab selection, GPU addressing, texture-hash identity |
| LevelConfig, NavMesh, TeleportValidation, DialogId, AetherEnergyLock, MatrixShockWave, BambooRaft, MissionArea, SubGame, WorldEntityRegistry | `levelconfig_binary`, `navmesh_binary`, `teleport_validation_binary`, `memorypack.tables`, `aether_energy_lock_binary`, `matrix_shockwave_binary`, `gameplay_compact_binary` | exact | consumers |

The selected Lizhiyan combo and Pograni ultimate SkillData copies now close as
whole stored records through source-specific static and executed-cursor joins.
Those joins are nonpublishable diagnostics; this table still describes the
current complete family gate and its remaining residue.

## Measuring a boundary, and the JsonData recovery order

A status says whether a reader closed a file, not how much of it is named.
`bytesConsumed` is how far a cursor reached: a tail-anchored framing reports
EOF while declaring an opaque prefix, which overstated LevelScriptData by more
than twenty points when read as coverage. `jsondata_schema_coverage` computes
`min(bytesConsumed, size)` minus the declared opaque spans in that reach; an
unreached tail and a declared opaque span are both unnamed. Its docstring
records the registry rules (`unmeasurable`, not-measured is never 0%, the
strongest reader per family) and the two tiers (reviewed `exact`, declared
`direct`); keep both reports side by side.

The parent [`game_data_recovery.md`](../game_data_recovery.md) owns the recovery
order. Use this measurement together with authenticated distinct-source
refusals to choose a shared dependency; byte coverage alone does not rank its
reuse. Buff event-map/root composition, LevelScript and template action routes,
and Skill's remaining named-schema joins have different admission gates.
Rerank first stops after the owning reader or complete gate advances.

Other families may have complete stored framing or schema-validated JSON while
their consumers, cross-file ownership and effective runtime values remain
unresolved. A closed file stops format work on unchanged bytes; it does not
close those higher-level questions.
An earlier declaration-derived pass reached EOF on every selected family; that
is a `direct` measure for its own input set and promotes no reviewed row.

## MemoryPack wire rules the member lists do not state

Each rule is enforced in code; the module named carries the reasoning.

- **Union tags are ranks**: the case-insensitive rank of the wrapped type's
  full name among the family's wrappers (`levelscript_union_layouts`), read
  whole from large native switches (`memorypack.union_dispatch`, which also
  reads a table kept in a cold section behind a hot-case compare, as in
  `SpawnerActionData`, and a short linear compare chain when no table
  resolves, as in `PatrolSubActionData`, under the same one-for-one rule) and
  ranked for other compare-chain unions (`memorypack.union_subtypes`,
  `structuralOnly`).
  Reviewed rows are `exact`, derived rows `direct`.
- **Never write a union tag as a literal**: updates renumber every later type.
  Resolve by type name (`levelscript_union_tags`) and key contract rows by it.
- **Members are the wrapper's setters in declaration order**, base chain
  first (`memorypack.wrapper_members`); that, not field order, is the wire.
- **Framing is decided by position**: object members go through the
  enclosing formatter (unmanaged ones raw), `List<T>`/dictionary elements
  through `T`'s formatter with a header, unmanaged `T[]` as a count plus raw
  elements, wrapper-less types raw everywhere (`_Cursor.declared_inner` in
  `codecs/levelscript/action_map.py`).
- **Memory images**: a struct without references is written raw at real field
  order and alignment with zero padding (`containsReferences`, `rawLayout`);
  `Nullable<T>` is flag, padding, value; a nullable count is `ff ff ff ff`;
  enum width comes from `value__`; union bases are abstract; static fields take
  no space; unmanaged `KeyValuePair` pairs carry zero padding (two declared
  sites: LevelScript `Dictionary<ulong,int>`, NavMesh `Dictionary<ulong,uint>`).
- **Check hand-written formatters first** (`FORMATTER_BACKED_TYPES`): every
  framing bug came from one. `AnimationCurve` writes wrap modes first and
  28-byte keyframes (`SERIALIZED_ORDER_OVERRIDES`, corpus-closure evidence);
  `BezierKnot` is a raw 56-byte value (`leveldata_bezier_knot_native`);
  `SendLuaEvent.manualValue` has its own writer
  (`codecs/levelscript/send_lua_event.py`). Unsettled formatters stay refused.
- **Contracts are re-proved, not re-pinned**: getter and EntityPtr readings
  are names re-checked on the installed build through `il2cpp.call_graph`
  (`entityptr_*_native`); equal body size never substitutes.
- **Two decoders must agree**: where the reviewed BuffData reader and the
  derived plan both read an item they end on the same byte or fail closed;
  derived-only items publish as `decodeStatus=derived`, tier `direct`.
- **Localising a desync**: blame the innermost live union tag (member errors
  collapse to a few subtypes), inject bytes after each member in turn, and
  check that the next union-array element starts with a valid tag marker. A
  desync surfaces far downstream as a plausible count, not where it began.

## Eliminated readings

Each was tested and refused; do not retry it.

- Ranking the flattened wrapper name: reproduces every reviewed row yet
  mis-tags `IFixAction.Data`..`IFixAction3.Data` and six
  `GameConditionClientOnce<...>` instantiations.
- Reordering `RunePuzzleData` members to declaration order: moved the failure
  and closed nothing; the defect was `KeyValuePair` padding.
- Declared `position, eulerAngles` order for `PosRot`: gives eulers past 1300
  degrees.
- `FAnimationCurve` declared order and the eight-field `FKeyframe` struct:
  self-consistent but wrong parses.
- SpawnerConfig `preWarnEffectFixedRotation` as four floats: same width, wrong
  value (`Optional<Vector3>`).
- Refusing the `idRef`/`paramSource`/`pathSize` = `-1` triple: it is a getter
  reference with no id.
- `manualValue` member count from the wrapper property type (nine): the
  instance writes seven.
- MemoryPack version tolerance for a short member count: retested with every
  framing fix; a short count is always a desync symptom.
- Recorded alias of `OnEntityEnterTrigger` to its filter: the output is the
  entering entity (`validated_non_alias`).
- Corpus-fitting keyframe layouts: stalled; reading the hand-written
  formatter's method list (`SerializeKeyFrame`) solved it.
- The TargetSettings byte "envelope" and the `CreateBuffActionInput` string
  scan: byte-shape heuristics replaced by member reads.
- Interleaved 32/56-byte BundleManifest records: the widths are a capacity
  accounting unit over split slot and value arrays.
- A four-byte width for every `fb_main` `SingleGrid` vector, and byte widths
  for `FBStreamArea` `RootVisible`/`AreaVisibleGroups`.
- Standard XXH3 for every StringPathHash row: the VFS implementation branches
  at exactly 128 UTF-8 bytes.

## What each corpus gate proves

Commands are in [`../../scripts/README.md`](../../scripts/README.md). Every
gate reauthenticates its rows against the current VFS ledger and live
fingerprints at both ends; partial `--max-files` probes write only to `tmp/`
or `scratch/` and never count as complete-corpus evidence.

| Gate | Establishes | Leaves open |
| --- | --- | --- |
| `streaming.corpus` | block-15 subgraphs, row prefix/slot partitions, native row-field representations, numeric/Global filename relations | runtime logical file, key namespace, names |
| `streaming.marker17_corpus`, `.marker13_corpus`, `.marker2_corpus`, `.marker15_gap_corpus` | the marker profiles above; physical gaps kept separate from native read windows and opaque complements | record fields, runtime selection |
| `memorypack.skill_corpus` | SkillData prefix/terminal framing; whole-schema rows only through replayed cursor receipts; cross-input-set rebinding only by explicit opt-in | the residue, provider/cache choice |
| `memorypack.skill_cursor_receipt`, `.skill_timeline_cursor` | observed cursor ranges; candidate child-action ranges where native route, reader contract and `buff_actions.Reader` agree | parent closure from candidates |
| `memorypack.buff_corpus`, `.buff_1b_corpus` | BuffData outer frame, event prefix, root continuation, named middle, accepted suffix; tag `0x1B` against its selected reader | interior bodies, provider selection |
| `memorypack.npc_montage_corpus`, `.lipsync_corpus` | exact EOF closure of every current file | runtime playback |
| `il2cpp.context_audit` | static formatter-identity chain and bounded SkillData samples on the selected build | executed cursor, runtime provider |
| `jsondata_corpus` | block-wide identity join and per-file terminal state | anything a family gate owns |

## Remaining gaps

- JsonData union-route residues (order above) and BuffData interior grammars.
- Terrain block/channel meaning; Streaming runtime-root joins, field-5 key
  namespace and nested target extents; BundleManifest live lookup and object
  ownership; IFix activation; runtime selection for every closed schema.
