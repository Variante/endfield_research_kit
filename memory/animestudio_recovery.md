# AnimeStudio recovery

This is the durable memory source of truth for the local
`tools/AnimeStudio` fork and its Endfield exporter behavior. User-facing
commands stay in `README.md`, wrapper contracts in `scripts/README.md`, and
operational detail in `.codex/skills/animestudio-workflow/`. Gameplay meaning
belongs in `game_data_recovery.md`; asset relationships belong in
`asset_recovery.md`; retail rendering interpretation belongs in
`character_render_and_animation_recovery.md`.

## Current conclusion

AnimeStudio is a reliable extraction layer for this repository. It can index
both Endfield VFS roots, stream or dump selected blocks, build asset maps,
export WebUI-facing Unity objects, decode Wwise media, and preserve partial
MonoBehaviour or shader evidence without turning a recoverable object-level
gap into a lost export.

The remaining work is certification and semantic depth, not basic access:

- a successful wrapper run proves stage health, not that every asset bundle or
  object was warning-free;
- `$partial` JSON is intentionally queryable evidence, not a clean decode;
- shader bytecode extraction is substantially recovered, while complete
  source-level decompilation and live binding selection remain outside the
  exporter;
- selected AnimationClip, Texture2D, Animator, Sprite, and managed-reference
  failures have guarded fixes, but future Unity variants must still fail
  visibly;
- per-AB clean/partial/error certification is not complete for every export
  type.

Treat the latest export summary and status manifests as current truth. Old
dated warning counts are useful only for explaining why a fix exists.

## Maintained workflow

Build the tracked CLI:

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Expected executable:

```text
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
```

Use the root wrappers for ordinary work:

```bat
.\export.bat --export-from-game
.\export.bat --export-from-game --with-assets
.\export_assets.bat --export-from-game
```

`export.bat --export-from-game` owns the structured Story refresh.
`export_assets.bat --export-from-game` skips the structured dump, writes a
lightweight VFS index, exports the WebUI-facing image/model/Material surface,
and decodes CN audio. The combined `--with-assets` path shares one AnimeStudio
run when Story and assets both need an installed-game refresh.

Production structured export continues to skip the broad world-streaming
blocks by default. Repeatable `--world-scene-chunk MAP:X:Z` selectors provide a
bounded exception: they dump the matching `InitChunkData` and
`StreamingChunkData` records from the `Streaming` block for `StreamingAssets`
only. Coordinates use the 128-unit world grid (`floor(X / 128)`,
`floor(Z / 128)`). The map02 cell at `(305.328, -1609.578)` resolves to
`map02:2:-13`; the installed VFS contains `InitChunkData_2_-13_0_0.bytes`
(398,788 bytes) and `StreamingChunkData_2_-13_0_0.bytes` (81,848 bytes).
These are proprietary static-scene payloads, not a Unity `.unity` scene or an
OBJ, so extraction preserves placement evidence but does not itself decode the
scene graph.

The combined scope must not asset-map-filter its `json_by_type` stage. Story
`TextAsset` DialogTree sources can sit outside the generated asset map; filtering
the combined JSON load drops authored option anchors and branch routes even
though the AnimeStudio command succeeds. Asset-only JSON work may remain
map-filtered, while Story-only and combined Story+asset JSON loads stay broad.

AnimeStudio JSON now preserves source offsets needed for exact CAB-scoped PPtr
audits. Top-level `$animestudio.sourceOffset` identifies the owner object;
every serialized PPtr carries `resolutionStatus`, and non-null references also
record the expected target source/CAB plus local or external source metadata.
Resolved references include `targetSourceOffset`. A focused installed-CHK
probe produced 14,869 resolved, 9,421 external-target-unavailable, and 9,210
null references, confirming that dependency-file indices can be checked
without treating an unresolved external target as a filename or global PathID
join.

Material JSON now also preserves the serialized keyword arrays, lightmap and
instancing flags, custom render queue, string tags, and disabled shader-pass
list. These fields are required to distinguish an authored transparent
Forward-only effect from an opaque fallback even when both reference the same
mesh. Shader bytecode sidecars inspect each extracted DXBC `SHDR`/`SHEX`
version token and publish `DecodedProgramStage` plus
`DecodedProgramEncoding=DXBC`; `SourceSerializedProgramStage` remains as raw
container evidence because Endfield combined payloads can label both embedded
programs as vertex. The Zhuang Fangyi piaodai audit uses this distinction to
pin its selected three-sample and four-sample vertex/fragment pairs instead of
trusting the misleading outer label.

The normal type-job mode is `auto`: map-filtered JSON requests are merged, while
broad Story JSON types run sequentially in isolated processes so a large
MonoBehaviour load cannot starve later TextAsset export. Map-filtered conversion
stays sharded. Use `parallel` only for comparison with concurrent per-type jobs,
or `merged` for an explicit broad merge experiment. Worker and shard counts are
separate controls; lower `--animestudio-jobs` when memory is tight without
assuming that fewer shards are always desirable.

Direct CLI calls are for bounded reproduction only. The integrated VFS
subcommands are:

```bat
AnimeStudio.CLI.exe dump --help
AnimeStudio.CLI.exe audio --help
AnimeStudio.CLI.exe stream --help
AnimeStudio.CLI.exe vfs-index --help
AnimeStudio.CLI.exe list --help
```

`dump`, `audio`, `stream`, and `vfs-index` must accept
`--fallback-assets`. `dump`, `stream`, and `vfs-index` accept repeated
`--block-type` and `--file-regex` filters. Both `StreamingAssets` and
`Persistent` matter. The wrappers configure them as sibling fallbacks in both
directions because authoritative block metadata and chunks may live in either
root. Fallback resolution applies to the encrypted `.blc` block metadata as
well as `.chk` payloads. An existing block directory whose `.blc` is missing
from both roots is an integrity error; do not downgrade it to an omitted block.

The audio command accepts `--shared-output` so one `--block all` process can
write common Audio/InitAudio/AuditAudio media separately from the selected
language voice block. `scripts/build_audio.py` uses this once per VFS source,
using `Persistent` as the fallback for missing metadata/chunks instead of
decoding the same logical PCK set again with the roots reversed. AnimeStudio
extracts one PCK at a time and caps converter concurrency at eight by default,
avoiding the former all-PCK retention and logical-CPU-sized converter fan-out.

`vfs-index --jsonl` is the compact streaming source for original-data update
snapshots. It preserves the default JSON document mode while emitting ordered
header/block/chunk/file/summary records that can be loaded into SQLite without
materializing the duplicated full index. Snapshot consumers must reject
truncated summaries, missing chunks, duplicate logical identities, and newly
missing blocks before treating a scan as promotable.

## Export and status model

Keep these distinctions explicit:

- **VFS-understood**: the indexed block/chunk exists and can be read.
- **loaded**: the Unity container/object entered the selected parse surface.
- **converted/exported**: an output or an intentional empty marker was written.
- **partial**: useful fields were preserved but a body or semantic label is
  incomplete.
- **certified clean**: the source/object has explicit status evidence showing
  no warning, conversion error, missing dependency, or unexplained absence.

These are not interchangeable. The historical AB census covered `Bundle`
entries directly, while asset maps also contained objects from
`InitialBundle`. Aggregate success logs could not certify every AB clean.
Status manifests are the maintained path toward that proof.

Primary diagnostics after a wrapper run:

```text
reports/export_full_summary.md
reports/export_full_summary.json
reports/StreamingAssets/*.stdout.log
reports/StreamingAssets/*.stderr.log
reports/Persistent/*.stdout.log
reports/Persistent/*.stderr.log
export_full/recovered/AnimeStudio-cli/animestudio_type_manifest.json
export_full/recovered/AnimeStudio-cli/<source>/asset_status/
export_full/unresolved/failed_to_decode.txt
export_full/unresolved/manifest_reference_missing.txt
```

An `Export ... error` is an object conversion failure inside a stage; other
objects in that process may still export. A nonzero AnimeStudio process is a
wrapper failure. A `metadata-only JSON` or `$partial` marker means the object
survived with bounded evidence after schema recovery stopped.

Do not claim a clean export from zero process failures alone. If a clean
certificate is required, extend the per-source/per-type status surface to map
every selected object and AB to clean, intentional-empty, partial,
conversion-error, not-loaded, or dependency-blocked evidence.

## Selection, dependency, and output identity lessons

Several former “missing output” families were selection or identity bugs, not
unsupported formats.

### Texture2D and Sprite

- Zero-width/height `Font Texture` objects with no image bytes or stream data
  are real Unity placeholders. They should emit intentional-empty status, not
  a decode failure.
- Many historical Texture2D misses used an asset-map name that differed from
  the real `Texture2D.m_Name` for the same PathID. Exact filter data or the
  actual object name exported valid DXT5, BC7, RG16, RGBAHalf, and RGBA32
  payloads. PathID/source identity is stronger than a stale map-row name.
- Texture2D rows can have different raw serialized hashes while sharing the
  same exported `Name + PathID` identity and byte-identical PNG. The status
  class `same_asset_id_output_reference` records this expected reuse; it is
  not a generic suppression for other types.
- Sprite conversion requires linked Texture2D and SpriteAtlas parse
  dependencies. A selected export type is not necessarily the complete parse
  surface needed by its converter.

### Animator and model conversion

Animator FBX conversion requires the linked hierarchy and render payloads:
GameObject, Transform/RectTransform, MeshFilter, renderers, Mesh, textures,
materials, Avatar, controllers, and AnimationClips. Explicit Animator filters
now add these as parse-only dependencies unless they were requested for
export.

FBX filenames include source path IDs so duplicate natural names cannot
overwrite one another and status manifests can identify ownership. An
Animator with no renderable mesh writes an `.fbx.empty.json` marker. A no-mesh
marker is a valid classification, not proof of a parser error.

### Output collision policy

Reserve final paths through the common output allocator. Never infer one
source object per natural filename. Collisions must retain source root, type,
PathID, and where useful raw hash/container identity. Reuse is acceptable only
when an explicit status class proves the objects share the same export
identity or decoded bytes.

## AnimationClip recovery

Unknown custom curve bindings once caused the whole AnimationClip export to
fail. The converter now preserves the curve under a stable diagnostic name:

```text
unknown_<Type>_<attribute>
unknown_CustomType<byte>_<attribute>
```

Known failing shards replayed with complete output after this change. The
placeholder keeps curve data and binding identity; it does not assign runtime
meaning to an unknown attribute. Light, particle-force-field, custom type 39,
and other future bindings should use the same fail-visible policy.

AnimationClip extraction and retail animation behavior are separate scopes.
Controller state, facial/morph routing, root motion, events, FX, and secondary
physics require downstream evidence even when every `.anim` file exports.

## Shader recovery

Shader recovery has four layers:

1. Unity Shader metadata and subshader/pass/program structure.
2. Packed program records and bytecode sidecars with provenance.
3. Backend decoding/disassembly such as DXBC and SMOL-V/SPIR-V.
4. Higher-level semantics, resource binding, variant selection, and renderer
   reconstruction.

The exporter substantially solves layers 1-3 for observed current samples;
layer 4 belongs to downstream render recovery.

### Blob layout and graceful fallback

Some Endfield shader blobs do not match the legacy Unity
`ShaderSubProgram` layout. Full conversion still runs first. When the packed
layout is unsupported, AnimeStudio writes parsed shader metadata plus an
explicit bytecode-unavailable classification instead of dropping the shader.
Unexpected native decompiler failures remain separate errors.

The recovered outer layouts include program tables, snippet bounds, backend
tags, keyword/variant context, and raw bytecode slices. Do not broaden a
reader from one signature without exact bounds and population validation.

### SMOL-V

Endfield Vulkan payloads are standard SMOL-V encoding version 1, not an extra
encrypted layer. The local decoder was updated to:

- separate the SMOL-V encoding byte from the SPIR-V version;
- support encoding versions 0 and 1;
- include version-1 opcodes and compact `MemberDecorate` runs;
- use the modern zigzag ID-delta path; and
- bound varints/raw words to the snippet rather than the enclosing stream.

Targeted and shard audits eliminated the former bad-ID and overrun failures.
This proves container decoding, not readable HLSL reconstruction.

### Bytecode sidecars

Sidecars retain shader identity, source root, PathID, subshader/pass/stage,
platform/backend, keyword context, packed bindings, hashes, and raw program
bytes. They are the durable bridge from AnimeStudio extraction to
Ruri.ShaderDecompiler, SPIRV-Cross, source-graph queries, and the Unity render
lab. Preserve unknown fields and raw bytes; never replace them with a guessed
binding solely because a later shader happens to look similar.

The opt-in bridge also emits Ruri `SerializedProgramData` JSON. It preserves
struct parameter indices/sizes, multisample flags, pass names resolved through
Unity name indices, common plus variant parameter tables, resource records,
descriptor sets, source subshader/pass/stage, compiled keywords, platform, and
hardware tier. This is sufficient to distinguish hundreds of serialized
keyword variants without relying on scratch filenames. The recovered Skin
`ForwardLit` export, for example, contains 456 Vulkan SPIR-V records forming
228 distinct original keyword sets and two embedded execution stages.

Endfield Vulkan binding indices use a verified packed form:

```text
high byte       flags
bits 16..23     descriptor set
low 16 bits     binding
```

For example, `0x89030008` is a texture at set 3/binding 8,
`0x09030001` is a sampler at set 3/binding 1, and `0x0D020000` is a
constant-buffer binding at set 2/binding 0. Keep the raw packed value beside
the decoded fields.

The lab helper
`unity_endfield_graph_shader_lab/tools/enrich_ruri_shader_metadata.py` reflects
SPIR-V and fills a missing UBO binding only when block size and every known
member offset yield one unique match. Partial Unity constant buffers permit a
bounded reflected tail; ambiguity stays unresolved, and `--strict` fails when
anything remains. This recovered the complete named UBO set for selected
Wulfa/Zhuangfy Skin/Eye and shared brow variants, including global, light,
shadow, per-material, cookie, ray-tracing, and ECS-per-draw buffers.

The selected Wulfa Skin module
`2543_endfield_spirv_1.spv` (SHA-256
`CF2AD23DF75208A1D1DB5651D36877B9EEF6AD9C90E28B43AB91C99327555913`)
resolved to this exact UBO layout:

```text
set 3 binding 27  ShaderVariablesGlobal       4512 bytes
set 3 binding 25  _LightDataBuffer            32864 bytes
set 3 binding 24  _RTPunctualLightGlobalData  32784 bytes
set 3 binding 26  ShadowData                   11440 bytes
set 1 binding 11  UnityPerMaterial               384 bytes
set 3 binding 28  LightCookieCB                 2560 bytes
set 3 binding 23  _RTRCBuffer                    208 bytes
set 2 binding 0   UnityInstancing_ECSPerDraw   16384 bytes
```

The 384-byte material block was seeded by 368 bytes of serialized Unity
metadata. Selected Eye variants similarly required accepting a 336-byte
serialized seed inside a reflected 400-byte block, which is why exact-size-only
matching is insufficient.

Pass identity and embedded-program stage are separate. One selected Wulfa Skin
module previously labeled “forward” is actually inside serialized
`RayTracingReflection`; `SourcePassName` is authoritative for the containing
pass, while each embedded SPIR-V execution model is authoritative for its own
stage. `PhysicalStorageBuffer64` modules may require GLSL rather than HLSL.
Metadata recovery proves symbols and resource layout, not live buffer values,
render scheduling, proprietary culling, or temporal state.

## MonoBehaviour and managed references

The default is `serialized-first`. Embedded serialized type trees often carry
more usable Endfield layout than locally generated DummyDll stubs.
`script-first` is an experiment flag and must fall back cleanly.

DummyDll behavior:

- `tools/DummyDll` is the preferred local root when present;
- wrapper flags or `ANIMESTUDIO_DUMMY_DLLS` may override it;
- missing, incomplete, or stale DummyDlls warn and continue;
- script metadata helps identify fields/types but is not a payload boundary
  until replayed against real serialized bytes.

External `MonoScript` identity is independently recoverable from Unity's own
CAB dependency table and PPtr, even when the matching managed type is absent
from the local DummyDll set. The dependency-aware
`cutscene_e11m1_dg011_2` probe resolves
`CAB-a7c1831c3f9527f9d6e7b6b9dc902957` / PathID
`-4087699526387706716` to
`Beyond.Gameplay.View.CutsceneRootComponent` in `Gameplay.Beyond.dll`, whose
`MonoScript` is PathID `-4607311172223566074` in
`CAB-5f527d7b7706baccdad9f794cf46420c`. Its embedded serialized TypeTree remains
valid while script-derived recovery reports `typeDefinitionNotFound`; that
status does not weaken the original PPtr or serialized layout. Exported
`MonoScript` JSON now carries the same `$animestudio` source/PPtr provenance as
other JSON objects plus class, namespace, and assembly.

The CLI's opt-in `--object_index_jsonl FILE` path writes compact `object`,
`schema`, `monoScript`, and terminal `summary` rows while decoded objects and
their dependency context are resident. Object identity is the complete
`(serializedFile, normalized source, sourceOffset, signed PathID)` tuple;
non-null PPtrs preserve expected external and resolved target identities.
Identifier-like scalars and typed identity/state integers are retained, while
prose, curves, vectors, floats, null PPtrs, and other bulk values are omitted.
The final file is published only after the terminal summary is written. A
maintained multi-process wrapper merge now writes unique per-worker parts and
deterministically publishes compressed object/schema streams plus a last-written
summary commit marker. It rejects incomplete/conflicting parts and promotes an
external reference only when external CAB filename plus signed PathID resolves
to one complete physical identity across the full merged index. PathID alone
and AnimeStudio's filename-first runtime cache are not sufficient global
identities. Published summaries carry a current source inventory fingerprint
plus content-hashed CLI apphost, first-party managed-assembly, and optional
DummyDll provenance; report-only loading fails closed when output hashes or
current provenance do not match. The installed source fingerprint is a
files/bytes/latest-mtime guard rather than a full multi-gigabyte content hash.

The first two-process original-bundle validation resolves
`CutsceneRootComponent` CAB `CAB-a7c1831c3f9527f9d6e7b6b9dc902957`, PathID
`-4087699526387706716`, through `_director` to PlayableDirector PathID
`596938598417355940`, then through `m_PlayableAsset` to TimelineAsset CAB
`CAB-c6363dc615901d4bdcddb393dd5bea77`, PathID `2345692907648257410`. The
merged component contains 7,476 objects, 1,018 MonoScripts, 73 schemas, and
7,450 exact external resolutions. The complete reachable component contains no
mission or quest carrier, so this exact Unity-object chain creates zero Mission
Pipeline bindings; it is a validated negative boundary, not a filename-based
cutscene ownership claim.

The corresponding exact-object census contains 26,318 PPtrs, 13,919 exact
indexed PPtr landings, and 393 connected components with zero ambiguous
CAB/signed-PathID identities. Although 143 objects carry 55 exact Story ids and
six objects carry five typed timeline ids, zero scalar value equals any of the
490 authoritative mission ids or 4,461 quest ids—even before semantic-field
filtering. Therefore the current MonoBehaviour/PlayableDirector scope produces
zero safe same-object or PPtr-component mission bindings. A broader Story/all
index should add GameObject rows and `m_Component` edges before revisiting
mission-named components; 117 resolved GameObject targets are currently outside
the indexed type surface.

Managed-reference recovery combines type-tree structure, registry type names,
RID links, IL2CPP/DummyDll metadata, class-specific bounded readers, and a final
raw-word/aligned-string diagnostic. A positive managed-reference registry is
not itself a decoded payload. Preserve:

- declared class/namespace/assembly;
- RID ownership and referenced-object links;
- exact consumed byte range;
- named proven fields;
- residual bytes or `$partial` reason when the reader stops.

Reusable proven families include CharacterDisplay data, skeletal morph maps
and shader parameters, selected character/weapon/camera/animation handler
records, ability/enemy/projectile components, and many compact action or
condition payloads. Their gameplay meaning and current frontier belong in
`game_data_recovery.md`; the exporter rule is that every family reader is
guarded by observed counts, lengths, enums, paths, and final offsets.

Projectile JSON now avoids serializing a second raw-word copy after the guarded
structured tail consumes exactly. The full observed family across StreamingAssets
and Persistent validates effect-list assignment, alert-effect variants, sound
hashes, and final scalars with zero residual tail words. Keep `$partial` on
unproven enum/hash/runtime meanings, and classify those records as
`semantic-partial` in recovery audits rather than reopening their byte boundary.

Ability-entity recovery now has a similarly evidence-bounded split. Across all
161 StreamingAssets and one Persistent `AbilityEntityTemplateData` roots, the
custom reader consumes the inherited id/name, faction, counted GameplayTag,
recycle/fade, and component-RID prefix exactly and resolves all 833 component
links. The revisitable audit under
`scratch/animestudio/ability_entity_tail_clusters/` now backs a production
reader through `useFrameTick`: 158 roots consume 60 bytes and four keyed variants
consume 80/84/104 bytes. All 162 linked exact root-component mirrors match, all
malformed controls reject, and replay removes 9,852 raw bytes while preserving
every later word exactly. The following `surroundingConfig` reader consumes 92
bytes in all 162 roots, reducing residuals to 336-1,084 bytes. Fourteen linked
SurroundingMovementData mirrors and ten non-consuming BaseRotationData
next-boundary mirrors match. Surrounding failure is transactional, so the exact
prefix/opening/component links survive with the remaining tail raw. Production
recovery now stops before `followMountPointConfig`; the six opening scalars plus
surrounding enum/hash meanings remain qualified as metadata-order/semantic
inference.

The rare enemy `EffectActionCfg/OmitUseScaleBBTail` is also structurally closed:
an exact 80-word/320-byte bounded reader handles the two mirrored
`data_eny_0092_slbomb` occurrences while leaving the enclosing EffectActionCfg
semantic-partial. A full 156-file enemy replay preserved all raw hashes, kept
154 sibling variants on their original reader, and rejected a 79-word malformed
control. Field and enum meanings remain inferred.

Character target recovery now separates three nested managed-reference layouts
at their proven byte boundaries. `SelectorData` ends after one finder RID plus
the validator and post-processor RID lists; the following bytes belong to
`TargetSettings.enableAdvancedDirection` and its nested `DirectionSettings`.
A 28 StreamingAssets plus two Persistent asset replay covers 74 occurrences of
each layout with zero fallback or residual. These records remain
`semantic-partial` for unnamed enum/hash values and unobserved non-empty
post-processors, target-context keys, or advanced direction source/target RIDs,
not for unfinished byte consumption.

Regenerate the MonoBehaviour frontier before ranking work. Old warning logs
predate many fixes, and console warning elimination does not remove honest
in-JSON partial markers.

## Memory and process behavior

Peak memory was driven by both unsafe lengths and valid large data. A single
historical TextAsset worker reached roughly 18.7 GB because decompressed VFS
and bundle blocks and large-object allocations accumulated.

Durable protections now include:

- reader-relative byte/count guards before allocations and loops;
- exact byte reads without redundant intermediate lists;
- object-relative `Remaining` bounds;
- guarded TypeTree, mesh, animation, bundle, VFS, and resource sizes;
- disposal of temporary streams and per-file object state;
- release of decompressed data and avoidance of unnecessary duplicate buffers;
- one shared wrapper worker pool with conservative parallelism controls.

These guards reduce corrupt-input risk and practical peaks; they do not make
each type equally cheap. Map-filtered conversion and very large TextAsset or
MonoBehaviour surfaces still warrant conservative jobs and process-tree RAM
measurement. Use benchmark reports rather than copying one machine's timing
into the workflow contract.

## Reproduction discipline

For a parser or conversion fix:

1. identify one exact source root/chunk, type, PathID/name, and prior signature;
2. build to an isolated output if the release binary is locked;
3. replay the minimal filtered object with Warning/Error logging;
4. verify output content and explicit status, not just exit code;
5. replay the affected shard or family to catch layout variants;
6. run the maintained wrapper only when the bounded test is clean;
7. update the latest generated report and this topic conclusion, not a new
   dated memory file.

Useful direct shape:

```bat
AnimeStudio.CLI.exe INPUT OUTPUT --game ArknightsEndfield ^
  --logger_flags Warning Error --group_assets ByType ^
  --export_type JSON --types MonoBehaviour:Both ^
  --filter_data FILTER.json ^
  --object_index_jsonl OUTPUT\objects.part.jsonl
```

Add `--dummy_dlls tools\DummyDll` only when script metadata is relevant. Use
`--map_op CABMap,Load` only with a compatible existing map when dependency
resolution is part of the repro.

## Recovery queue

1. Extend clean/partial/error/not-loaded status manifests from Texture2D-style
   coverage to every maintained conversion/JSON stage and source AB.
2. Keep the current MonoBehaviour frontier concentrated: continue recurring
   ability-entity fields from `followMountPointConfig` and character tails with
   guarded readers. The rare enemy EffectActionCfg tail is structurally closed;
   monitor it and projectile semantics unless a future
   exact-consumption guard fails, and preserve residual bytes on every failure.
3. Use the now-maintained opt-in merged object index and
   `scripts/story_recovery/build_animestudio_story_carrier_audit.py` to audit
   the next bounded original-data carrier families. The consumer accepts only
   exact actionable Story values in typed Story-id fields on fully decoded,
   schema-backed objects with resolved object/MonoScript type identity and a
   same-object typed mission/quest or scene/script id. It validates the merge
   commit marker, stage signature, and output hashes before scanning. The
   current installed-game Story export has published valid indexes for both
   sources. The current carrier census scanned 1,335,450 objects against 2,691
   actionable gap keys: 190 objects contained an exact target value, but zero
   passed the typed same-object Story plus owner/runtime gate. The visible
   examples are names such as `TimelineAsset.m_Name` and
   `CutsceneRootComponent._timelineName`; they remain rejected clues and add no
   edge. Keep exact external-PPtr ambiguity and unresolved counts visible,
   keep indexing opt-in until its complete-run cost is acceptable, and promote
   no mission edge without separately recovered native consumer semantics.
   The durable generated census is
   `reports/story/recovery/animestudio_story_carrier_audit.{json,md}`.
4. Normalize shader sidecar binding metadata enough for repeatable downstream
   lookup without claiming source-level semantics that the bytes do not prove.
5. Test future Texture2D/Sprite/Animator variants against PathID-based status
   and dependency closure; do not regress to name-only selection.
6. Continue memory work from process-tree measurements, separating shard size,
   worker count, type-job mode, and source root.
7. Retire dated warning snapshots after their root cause, guard, and remaining
   boundary are represented here or in the owning game-data/render topic.
