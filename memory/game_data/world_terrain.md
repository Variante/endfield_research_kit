# Terrain: `TRET` and native path families

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the lane map.

**Level 3, world lane.** `scripts/game_data/terrain/tret.py` owns the decoded
`TRET` framing; `scripts/game_data/terrain/height.py` reads the supported
`_H` grid shape for Map; and `scripts/game_data/terrain/corpus.py` gates a
current VFS corpus. The selected reader facts are in the reviewed
[`terrain_tret_native.json`](../../scripts/game_data/contracts/terrain_tret_native.json)
contract. The native path templates are separately recorded in
[`terrain_layer_paths_native.json`](../../scripts/game_data/contracts/terrain_layer_paths_native.json)
and checked by `scripts/game_data/terrain/layer_paths_native.py`.
The selected downstream tile-slot chain is recorded separately in
[`terrain_tile_slots_native.json`](../../scripts/game_data/contracts/terrain_tile_slots_native.json)
and checked by `scripts/game_data/terrain/tile_slots_native.py`.
The selected layer-result and render-property chain is recorded in
[`terrain_layer_slots_native.json`](../../scripts/game_data/contracts/terrain_layer_slots_native.json)
and checked by `scripts/game_data/terrain/layer_slots_native.py`.
The independent managed texture-resource copy chain is recorded in
[`terrain_virtual_texture_managed_native.json`](../../scripts/game_data/contracts/terrain_virtual_texture_managed_native.json)
and checked by `scripts/game_data/terrain/virtual_texture_managed_native.py`.

## Established structure

The `LAYER_C_*`, `LAYER_D_*`, and `LAYER_N_*` logical files are members of the
Terrain VFS block. After the VFS envelope is decoded, they begin with `TRET`.
The maintained reader checks the version and a 20-byte fixed prefix. The
selected UnityPlayer consumer reads the word at decoded `+14` as a
`GraphicsFormat`, checks the declared payload length at `+16` against its
allocation, and copies that many bytes from `+20`. The reader ABI does not
receive an input length, so the native contract alone does not prove final
source cursor; the corpus gate independently checks the complete decoded
file.

The observed `LAYER_C` layout has graphics format 5 and a one-byte-per-unit
footprint. `LAYER_D` and `LAYER_N` use formats 108 and 109, respectively. The
selected native enum names those two formats `RGBA_BC7_SRGB` and
`RGBA_BC7_UNorm`; its footprint table assigns both 4-by-4 blocks of 16 bytes.
The parser tiles their known mip-like ranges exactly, but keeps the contained
values anonymous. The selected reader passes decoded `+12` as an unsigned
numeric texture-setup argument and separately passes whether it exceeds one.
Its pattern is consistent with a mip count, but that exact semantic name
remains inferred. Current file counts, layout counts,
and input hashes belong to the generated Terrain corpus report.

A bounded, MD5-verified installed six-file tile with one scene and tile index
also parses exactly as `TRET`. `Terrain_*_H.bytes` is one 65-by-65 range of
two-byte texels and `Terrain_*_C.bytes` one 34-by-34 range of two-byte texels;
both carry GraphicsFormat 6, selected-native `R8G8_UNorm`. The `N`, `T` and
`A` files each have a 132-by-132 source axis tiled into 4-by-4 compressed
blocks; `N` and `A` carry format 101 (`RGBA_DXT5_UNorm`) and `T` format 100
(`RGBA_DXT5_SRGB`). `S` has a 132-by-132 range of four-byte texels in format
8 (`R8G8B8A8_UNorm`). The selected native enum names and format-descriptor
footprints are checked by `terrain_tret_native.json`; the corpus reader keeps
all contained values anonymous. The maintained `height.py` reader accepts
the `_H` shape and combines each pair as `byte0 + 256*byte1` for Map diagnostic
contrast. That display composite is not a proved height value or even a
proved relative relief ordering. The sample does not show which path the
runtime opened or how any payload is used. Its file hashes and exact header
words belong to the generated
`reports/terrain/path_family_sample.json`; `tret.py` and `height.py` are the
reusable checks for the structural claims.

The current full VFS ledger closes the path-family grouping as well as the
framing: every named `Terrain_*` tile key has all six H/N/T/A/S/C members,
and each suffix has one complete six-word header shape and GraphicsFormat
throughout the audited set, matching the six-file sample. Across scenes,
`LAYER_D` and `LAYER_N` have identical index sets; `LAYER_C` occurs only at
indices in those sets. The maintained
`terrain.corpus` gate checks those path joins, each logical file's outer
identity and complete `TRET` body, and reports family counts, formats, and
header shapes in `reports/animestudio/terrain_tret_latest.json`. These are
stored-file relationships. They still do not identify the decoded channels or
a renderer field.

Terrain constants in IL2CPP metadata are reached through the
`fieldDefaultValues` index and the compressed default-value data, as decoded
by `scripts/game_data/il2cpp/protocol.py`. Reading those bytes as ordinary
four-byte integers gives wrong values. Selected metadata examples include
`HGTerrainGroundLayer.TEXTURE_SIZE = 2048` and
`VirtualTextureRenderer.VT_CACHE_PAGE_RESOLUTION = 512`. Those constants
describe renderer configuration; neither establishes a `LAYER_*` destination.

The installed `UnityPlayer.dll` has a validated routine containing direct
loads of the exact templates `{0}/Layers/LAYER_C_{1}.bytes`,
`{0}/Layers/LAYER_D_{1}.bytes`, and `{0}/Layers/LAYER_N_{1}.bytes`. The
`layer_paths_native` validator gates the selected `GameAssembly.dll`,
`global-metadata.dat`, and `UnityPlayer.dll`, the routine's adjacent `.pdata`
entry, prelude, path and epilogue windows, its two formatter windows, the
control-flow links, and each literal load. The path window previously treated
as a whole function is a continuation after the entry and prelude. The gate
withholds all paths on a missing or changed build. The same checked code
allocates a 32-byte record, stores the numeric
argument used to format all three paths at record `+0`, initializes three
adjacent result slots, forwards each formatted path to one common helper with
the corresponding slot pointer (`D` at `+8`, `N` at `+16`, `C` at `+24`), then
appends the record to a collection. These are local record offsets, not
`VirtualTextureRenderer` field offsets. This proves one grouped path record
per numeric argument in the selected code; path construction alone does not
establish a texture binding or render use.

A later branch of that checked function takes a separate packed 32-bit tile
argument. Selected instructions split it into high 4, middle 14 and low 14
bits for path formatting, allocate a 56-byte record, and store the original
word at its start. The exact templates for `Terrain_H`, `Terrain_N`,
`Terrain_T`, `Terrain_A`, `Terrain_S` and `Terrain_C` each reach the same
formatter and common path helper, with six separate result slots. The checked
formatter receives the path root, then the high 4 bits, low 14 bits, and
middle 14 bits, in that order. Its selected bridge forwards the resulting
argument vector. The record is appended to a collection distinct from the
`LAYER_C/D/N` collection. `layer_paths_native.py` checks all nine literal
loads, both record layouts, the forwarding calls, packed-bit instructions,
formatter argument order and appends against six selected `.pdata` windows.
This proves two grouped path families and the construction of their
path arguments, not a join between them or a renderer destination. The
suffixes alone and the `_H` diagnostic composite do not name runtime
texture roles.

The selected downstream code closes a named render-property join for the
six-file tile family. A queue worker takes the path builder's grouped tile
record, conditionally moves its pointer into a ready vector, and calls a tile
callback. That callback resolves all six result slots into a temporary handle
vector. Its staging order is **H/N/T/S/A/C**, even though the record was built
in **H/N/T/A/S/C** order: the `A` and `S` handles exchange positions between
the record and the temporary vector. The tile consumer passes each handle to
the same guarded copy helper with a distinct owner-local destination. The
helper requires present inputs and matching numeric properties before its copy
call; the consumer can exit before any copy when owner data or tile
availability is absent.

The owner initializer constructs numeric property IDs from exact string
literals. A checked render-binding function reads the same six destinations
and pairs each with its corresponding ID; the binding helper forwards each
resource and ID together. The selected code therefore joins the tile path
suffix to these authored render-property names:

| Tile suffix | Selected render-property literal |
| --- | --- |
| `H` | `_HeightmapAtlas` |
| `N` | `_NormalmapAtlas` |
| `T` | `_TintColorAtlas` |
| `A` | `_AlbedoAtlas` |
| `S` | `_SplatCtrlAtlas` |
| `C` | `_CliffIndexAtlas` |

`tile_slots_native.py` authenticates the selected binaries, upstream path
record, queue transfer, slot staging, conditional copies, literal-to-ID
stores, and ID/resource pairing. Exact selected offsets and hashes live in its
reviewed contract and generated report. The literal names identify the
render-property route, not the encoded pixel channels, final GPU sampling, a
managed `VirtualTextureRenderer` field, or which installed paths were selected
at runtime. The separate `LAYER_C/D/N` record follows a different downstream
consumer.

That selected layer consumer closes the first destination hop for the grouped
`LAYER_*` record. A separate queue promotes the record, and its callback
resolves the three path-result handles in **D/N/C** order. It forwards the
handles and the record's numeric argument through an owner subobject. On the
accepted branch, a copy dispatcher pairs D and N with distinct owner-local
resource handles and calls a common copy helper. C reaches a third resource
handle only when its source is present and an owner-side availability check
passes. The helper compares source and destination properties before calling
a lower-level copy routine, which has further guards. These are conditional
native operations; the contract does not show which installed paths were
selected in a live run.

The owner initializer constructs property IDs from exact string literals. A
checked render-binding function resolves the **same three** owner-local
resource handles, reads their corresponding IDs and forwards each resource/ID
pair to the common property sink. The selected native join is:

| Layer path | Selected render-property literal |
| --- | --- |
| `LAYER_D` | `_Splats` |
| `LAYER_N` | `_Normals` |
| `LAYER_C` | `_ConeMaps` |

The `LAYER_C` binding skips its property call when its resource resolves to
null. `layer_slots_native.py` gates the selected binaries, upstream path and
tile dispatch contracts, the layer queue and callback, owner forwarding, the
three source/destination pairings, guarded copy helper, property-name literals,
ID stores, and resource/ID binding calls. Exact offsets and hashes live in its
reviewed contract and generated report. The property names establish the
render-binding route; they do not identify stored pixel channels, a managed
`VirtualTextureRenderer` field, shader sampling, or live file selection.

The selected `HGTerrainRenderer` constructor takes a `TerrainResource` value,
allocates a `VirtualTextureRenderer`, passes that same value to its constructor,
and stores the child in `m_vtRenderer`. It also copies the value's
`runtimeResources` and `configuration` references into its own fields. The
child constructor reads `runtimeResources.textures` and copies eight named
texture fields into corresponding renderer fields. The reviewed managed-native
contract checks the selected metadata identities, field offsets and types,
both registered constructor pointers, the parent handoff and assignment
window, and the child's complete assignment window, source loads, destination
stores, and write-barrier calls. The checked child field copies are:

| `TextureResources` field | `VirtualTextureRenderer` field |
| --- | --- |
| `splatIndexMap` | `m_splatIndexMap` |
| `splatControlMap` | `m_splatControlMap` |
| `terrainLayerDiffuseArray` | `m_splatsDiffuseArray` |
| `terrainLayerNormalArray` | `m_splatsNormalArray` |
| `normalmap` | `m_terrainNormalMap` |
| `colorVariationTex` | `m_colorVariationTex` |
| `heightmap` | `m_terrainHeightmap` |
| `deformableControlMap` | `m_deformableControlMap` |

The two layer-array fields have `Texture2DArray` type; the other six have
`Texture2D` type. The parent handoff requires child allocation, and the child
field copies require the source objects to be present. This directly joins the
`TerrainResource` argument to both managed renderers, then
`TextureResources` to the child fields. It is independent of the selected
UnityPlayer `LAYER_*` and six-file tile chains. No checked edge carries one of
those path-result handles into `TerrainResource.runtimeResources.textures`, so
no installed file is yet identified with any of these managed fields. A
matching word such as “splat” does not supply that missing edge.

The selected managed-native audit also scans every raw-backed
`GameAssembly.dll` section for the direct `E8` relative-call encoding targeting
the registered constructors. It finds no candidate targeting
`HGTerrainRenderer.ctor(TerrainResource)` and one targeting
`VirtualTextureRenderer.ctor`, at the checked parent handoff. This is a bounded
static call-encoding result. It does not exclude indirect invocation, patch
dispatch, or live use of the parent. In particular, the direct-call scan cannot
identify who supplies the `TerrainResource` argument, and cannot join the
separate UnityPlayer file handles to its `TextureResources` fields.

The same selected contract now checks a conversion handoff by registered
method identity and direct-call bytes. `HGTerrainConvertFunc.ConvertFrom`
receives a component, `FlatBufferConvertContextV2`, and entity transition,
then directly calls `HGTerrainV2.SetupFromParams_Phase1` on the reviewed
unpatched path. That phase directly calls one
`HGTerrainManager.SetupTerrainManager` overload, which directly calls its
second overload. This establishes a converter-to-manager route, including a
context argument at its entry. It does not establish which converted property
or texture is passed into a `TerrainResource`, nor connect the manager's
inputs to the separate `LAYER_*` owner-local handles. The converter and phase
also have iFix patch guards, so this static route is conditional on the
unpatched branch.

Within that selected converter route, four named `PropertySerializeId` static
fields are read from the checked `HGTerrainConvertFunc` class. Each ID and a
distinct local output address go to the same helper body, accompanied by a
`FlatBufferConvertContextV2.TryConvertAssetFrom<T>` MethodSpec whose generic
type matches the receiving argument. The converter then loads
those exact four local slots into typed `SetupFromParams_Phase1` arguments:

| Converter property ID | Phase 1 argument type |
| --- | --- |
| `PROP_ID_TERRAIN_CS` | first `ComputeShader` |
| `PROP_ID_TERRAIN_RTCS` | second `ComputeShader` |
| `PROP_ID_TERRAIN_PS` | `Shader` |
| `PROP_ID_SPLAT_INDEX_MAP` | `Texture2D` |

The managed-native contract checks the selected class usage cell, metadata
field identities and offsets, the complete request/argument code window, all
four MethodSpec usages and calls to the common helper, the four local output
and argument loads, and
the Phase 1 parameter types. This establishes the converter's property-ID to
setup-argument route. It does not establish the helper's returned objects,
identify the producer of `TerrainResource.runtimeResources.textures`, or join
these managed arguments to installed `LAYER_C/D/N` path-result handles. The
`SplatIndexMap` argument is a single `Texture2D`; it is not evidence that any
one of the three installed layer families populates the managed
`Texture2DArray` fields.

A selected-metadata review identifies `HGTerrainRuntimeResources` as a
`ScriptableObject`, with `TextureResources` as its nested reference type. The
`HGTerrainConvertFunc` static class also declares property IDs named
`PROP_ID_SPLAT_DIFFUSE_TEXTURE_ARRAY`,
`PROP_ID_SPLAT_NORMAL_RO_TEXTURE_ARRAY`, and
`PROP_ID_SPLAT_CONEMAP_TEXTURE_ARRAY`. A direct read census of the selected
`ConvertFrom` body finds no read of those three static ID fields: its checked
requests use the four IDs above, alongside separate terrain information and
array-data IDs. This bounds only that direct converter body; other methods,
indirect calls, and serialized asset loading are not excluded. The current
MonoBehaviour/PlayableDirector object-index schema sweep has no fields named
`terrainLayerDiffuseArray`, `terrainLayerNormalArray`, or
`deformableControlMap`, but that export does not cover every possible
`ScriptableObject` producer. Thus the authored ID names and the absent schema
rows do not bridge the native `LAYER_C/D/N` owner handles into
`TextureResources` or identify a live asset value.

## What remains inferred

In the audited file set, `D` and `N` have matching per-directory index sets;
`C` is sparse and its indices are a subset where present. The selected
render-property join names D as `_Splats`, N as `_Normals`, and C as
`_ConeMaps`, superseding interpretations based only on that pairing. The
property names do not prove the files' encoded channel meanings or which
installed file was selected in a live scene.

`VirtualTextureRenderer` receives `m_splatsDiffuseArray` and
`m_splatsNormalArray` from two separate `Texture2DArray` fields in
`TextureResources`; `m_colorVariationTex` comes from a `Texture2D` field.
A previous conclusion identified `LAYER_C` with
`m_colorVariationTex` by elimination, then rejected that identification from
the single-texture type, then reinstated it by proposing compositing. The
direct selected binding to `_ConeMaps` retracts that identification. It also
does not identify a managed field: a string-derived render-property ID, a
native owner-local handle, and a `VirtualTextureRenderer` field are distinct
evidence. The old per-layer mask suggestion has no direct field join either.

The tile chain still needs a checked runtime selection and shader sampling
witness to establish the visual effect of any installed payload. For
`LAYER_*`, the native property route is identified, but a shader sampling
witness is still needed to explain its visual effect. A separate runtime
selection witness must tie an installed path to a live copy. The selected
property names alone do not establish either result.

The next source to check is the common converter helper's returned-object
identity and the manager setup overloads' use of these four arguments.
Compare those identities with the native `LAYER_*` result handles; the four
property names alone cannot establish that join. An indirect-caller or
resource-producer trace for `HGTerrainRenderer.ctor` is the separate route to
the `TerrainResource` fields.
