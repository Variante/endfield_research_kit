# Unity assets: identity, and semantic bindings

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, Unity assets lane.** The `Bundle` block's payloads and what they can
be bound to. This topic owns semantic bindings between exported Unity assets and Story, characters, gameplay entities, world objects, audio, and video. The Assets page only inventories browser-visible files; AnimeStudio only extracts them.

Extraction correctness belongs to
[`extraction_pipeline.md`](extraction_pipeline.md); page publication belongs to
[`../webui/assets.md`](../webui/assets.md). This file owns the identity rules and
the binding evidence order that several pages and the source graph reuse.

## Current status

Stored collision geometry has a direct prefab-binding lane beside render
assets. [`unity_scene.py`](../../scripts/game_data/unity_scene.py) reads the
observed Endfield player GameObject, Transform and MeshCollider bodies through
EOF. It retains the GameObject tag/art-tag/active suffix that the handwritten
AnimeStudio GameObject JSON omits, and rejects another layout rather than
guessing. Raw hashes and selected VFS identity coverage belong to the caller's
gate. Local references join by physical source, offset, CAB and PathID.

A collider binding requires its GameObject component backlink, exactly one
declared Transform, each Transform's GameObject backlink, and reciprocal
parent/child edges through the full stored hierarchy. Composing root-to-leaf
TRS preserves parent rotation and scale; one child position alone is not a
placement, and opposite ancestor translations can cancel. A MeshCollider's
local Mesh PPtr can join a cooked triangle object with equal raw SHA256. This is a
serialized prefab relationship, not a live world instance or evidence of
activation. Per-object hashes, matrices and inventories stay in
`reports/assets/collision_prefab_review.json`; the reusable reader and source
class implementations preserve the durable interpretation.

[`unity_scene_corpus.py`](../../scripts/game_data/unity_scene_corpus.py) extends
that bounded probe into a reusable selected-Bundle gate. It authenticates the
current VFS ledger, selected physical chunks and exporter closure before fresh
scene/Mesh JSON and raw exports, then independently compares stored PPtrs,
TRS and collider settings with typed JSON. A saved extraction can be reanalysed
only after the same source, command/log and object identity/raw/JSON-hash checks.
Warnings, malformed bodies and incomplete selected-Mesh coverage are visible
failures. Export coverage alone never proves an absent class in a serialized
object directory. The GameObject layer is read but not retained by AnimeStudio's
handwritten class, so its absence from JSON is not a raw-body disagreement.

Wider stored-hierarchy checks establish that one exact cooked Mesh can be referenced by
several MeshColliders with different full ancestor transforms. Store the
binding and composed transform per collider identity; never assign a single
placement to the Mesh or infer its owner from the catalog container label.
Composed matrices derive from the stored float32 TRS values, and do not prove
the live engine's floating-point evaluation or later animation. MeshCollider's
`convex` setting selects which cooked buffer belongs to that component;
a stored hull without a checked consumer does not acquire runtime ownership.
The generated wider inventory is `reports/assets/collision_scene_current.json`.
The separate DynamicStreaming model placement and collider-control consumer
boundary is documented in
[`world_dynamic_streaming.md`](world_dynamic_streaming.md#model-instantiation-and-collider-control).
Its grid/parent transform route and collider-enable calls must not be promoted
to a live instance join merely because a stored prefab link is exact.

Convex consumer recovery requires crossing the referring prefab's serialized
external table. Its raw Mesh PPtr, the export's exact external slot and CAB
name, and a unique fresh target CAB jointly select the full physical Mesh
identity. A missing target remains unavailable; duplicate physical locations
for one CAB are ambiguous. A bare PathID or a catalog container label never
substitutes for this check. The selected scene gate accepts `AssetBundle`
physical selectors with `PathID=0` for container discovery; those selectors
assert no Unity object identity. The current widened inventory is
`reports/assets/collision_convex_owners_current.json`.

[`unity_asset_bundle.py`](../../scripts/game_data/unity_asset_bundle.py) reads
the Endfield AssetBundle name, path flags, preload table and container prefix
independently of typed JSON. It bounds each preload span and retains the rest
as an opaque tail. Only a container entry's actual GameObject PPtr can label
a proved hierarchy root as a prefab asset; a preload dependency is not
ownership. The scene gate checks the prefix against JSON and protects both
raw and JSON bytes in its extraction receipt. This closes stored triangle and
convex prefab bindings without claiming to decode unrelated Bundle tail fields.

The scene gate's receipt API recomputes these joins from an admitted saved
extraction without launching AnimeStudio. It checks canonical ledger locations
so equivalent relative and absolute paths can reuse one receipt, while retaining
all source/content/selection gates. Consumption snapshots cover the selected
VFS inputs, exporter closure, raw/typed objects and receipt. The Assets projection
publishes exact per-collider prefab ownership through this API; unknown live
instances and placement remain separate from the stored hierarchy.

[`unity_scene_meshes.py`](../../scripts/game_data/unity_scene_meshes.py) can close
external Mesh targets missing from a saved scene extraction by composing it with
an independently admitted cooked-Mesh corpus from the same current input set.
The raw referring PPtr, its exact exported external-table slot and unique
physical target CAB remain mandatory. Target raw/cooked bytes are rejoined and
complete format readers run before admitting geometry. Ambiguous or absent
targets remain unresolved. The result uses a separate stored-collider Mesh-join
schema and retains both selections; it does not widen the scene-body census or
require another export or runtime capture.

Those admitted surfaces and reciprocal Transform chains are sufficient for a
stored collision assembly. Keep each collider reference as a separate part,
compose the root's stored TRS as well as its descendants, and group only by the
physical root GameObject identity. Such a projection establishes authored
relative geometry, including disabled definitions, rather than runtime physics
or world placement. Selected coverage also leaves primitive bodies other than
separately admitted boxes, custom and unselected colliders outside the reconstruction. The Assets owner
documents preview/publication behavior in its page recovery guide.

[`unity_box_corpus.py`](../../scripts/game_data/unity_box_corpus.py) owns the
supplemental stored BoxCollider scope. Its producer selects only physical
AssetBundle spans in an admitted scene receipt, exports BoxCollider and
AssetBundle raw/typed bodies with the same current exporter, and checks exact
raw/JSON coverage and the original Bundle hashes. The serialized field-path
sequence and an independent EOF reader prove GameObject/material PPtrs,
options/tag words, the surface byte and boolean flags, full size and local
center. A reciprocal GameObject component declaration and complete stored
Transform chain are mandatory. Only an actual AssetBundle container GameObject
PPtr establishes a prefab root; preloads and names do not. Saved derived rows
are recomputed after source/producer/selection/log/raw hashes and consumption
snapshots pass. This does not widen the original scene or cooked-Mesh receipt,
prove other primitive layouts or make missing exports evidence of absence.
Stored box corners can be projected through the authored Transform chain; this
is not a claim about live nonuniform-scale/shear handling or PhysX attachment.

[`unity_render_corpus.py`](../../scripts/game_data/unity_render_corpus.py) adds
a separate selected MeshFilter/MeshRenderer supplement, using the shared
[`unity_scene_supplement.py`](../../scripts/game_data/unity_scene_supplement.py)
producer/source/census gates also used by boxes. The original scene receipt's
scope stays unchanged. The reviewed
[`unity_render_layouts.json`](../../scripts/game_data/contracts/unity_render_layouts.json)
field-path sequences and [`unity_render.py`](../../scripts/game_data/unity_render.py)
independent EOF reader establish the stored component header, material PPtr
order, static-batch fields and additional vertex-stream pointers. Renderer and
MeshFilter must declare the same reciprocal GameObject, and the complete
Transform chain must reach an actual declared physical prefab root. A missing
MeshFilter remains a gap, not an invented Mesh selection.

The current dedicated AnimeStudio JSON branch supplies no PPtr-reference
witnesses for these typed classes, and its MeshRenderer constructor omits the
final Endfield Enlighten vertex-stream PPtr. The independent raw reader retains
that tail; absence from typed JSON is not evidence of a null pointer. External
file slots can reuse an authenticated MeshCollider slot witness from the same
physical serialized file. Each witness's referring raw pointer, CAB/path and
source hashes are checked; another file's equally numbered slot cannot bind.
Unwitnessed slots, excluded target bodies and ambiguous physical CABs remain
distinct gaps. An exact admitted Mesh target identity proves a stored resource
reference, not decoded render geometry, material appearance or runtime drawing.
Other Renderer classes remain outside this supplement. Its Assets projection
joins collision and render components only through that physical prefab root;
names, dimensions and preload adjacency never establish ownership.

[`unity_source_directory_corpus.py`](../../scripts/game_data/unity_source_directory_corpus.py)
can now extend that selection with complete serialized directories and resource
bodies. Its offline sidecar references the admitted AnimeStudio libraries without
rebuilding the CLI. Each physical Bundle is loaded separately, with explicit
filter offsets; metadata, selected-class bodies and owner-archive resource spans
are retained. [`unity_serialized_directory.py`](../../scripts/game_data/unity_serialized_directory.py)
independently closes the v22 header/metadata region, object spans and ordered
external table. [`unity_type_tree.py`](../../scripts/game_data/unity_type_tree.py)
independently decodes declared fields through body EOF and checks complete generic
JSON, preserving primitive float widths. Byte-buffer bounds are distinct from
compound-item budgets. Unknown layouts and invalid spans fail closed.

The generic stored Material view retains texture UV-set indices, double-sided
GI and trailing fields absent from the dedicated constructor's JSON. These are
stored definitions, not selected runtime shader features. The Endfield Mesh
branch omits CompressedMesh only when its preceding raw baked-collision boolean
selects that branch. [`unity_mesh.py`](../../scripts/game_data/unity_mesh.py)
reads selected uncompressed vertex streams and complete triangle submesh ranges;
the packed normal selector admits signed-10 octahedral directions, while runtime
tangent frames remain outside the projection. Mesh stream bytes must be the exact
declared range of its own CAB archive resource. Filesystem-search fallback cannot
admit a resource. UV0 and UV1 remain separate stored channels.

[`unity_texture.py`](../../scripts/game_data/unity_texture.py) independently
closes selected unstripped, single-image Texture2D block-compressed mip chains.
Every mip has its declared dimensions and block footprint; the complete byte
census must agree with the exact owner-archive range and stored image size.
Unsupported platform layouts, stripped mips and other texture dimensions remain
unavailable. [`unity_texture_decode.py`](../../scripts/game_data/unity_texture_decode.py)
supplies only the admitted top mip to the existing AnimeStudio codec through a
separate managed sidecar. Managed and native codec libraries come from the same
admitted CLI closure; no filesystem codec fallback or CLI rebuild is used.
Decoded pixel lengths/hashes and the complete output census are checked before
PNG projection. The PNG retains decoded channels and flips rows for exported
image coordinates, with no gamma conversion or normal reconstruction. Stored
UV-set, tiling, offset, sampler and colour-space fields are definitions; they
do not establish active shader roles, runtime sampling or material overrides.

The admitted Shader body also retains its parsed-form name and property
declarations, even when the root object's name is empty. Compare each non-null
stored Material texture key against that exact Shader's declared property list;
this is a `structuralOnly` declaration match, not a compiled sampler binding or
runtime keyword-selection claim. The same complete generic body reader makes
this check independent of filename conventions or texture suffixes.

The maintained [`shader/`](../../scripts/game_data/shader/) readers extend this
join into baked compiled programs. Plain LZ4 segments are consumed exactly;
segment zero owns the program directory and each record names its actual data
segment. Complete compressed and decoded range censuses precede interpretation.
For D3D, native code-envelope ranges close against complete DXBC containers,
whose token headers establish executable stages. A serialized vertex-program
carrier can contain both vertex and fragment executables; its field name must
not substitute for token evidence.

Stored LOD/pass/player indices join code, keyword names and parameter records.
Parameter framing admits a unique complete resource/descriptor suffix only
after whole constant-buffer rows, including nested structs. Descriptor-set IDs
are stored keys and can be sparse; requiring an ID to equal its row ordinal was
an AnimeStudio parser defect. Duplicate IDs, out-of-range IDs and malformed
binding maxima still fail closed. Unknown header and packed descriptor words
remain explicit, and unsupported non-D3D records retain an opaque boundary.
This does not prove GPU upload slots, runtime constants or sampler application.
The sparse-ID source correction was checked with isolated compiled parser
fixtures; the production CLI was not rebuilt for this correction. The offline
reader supplies these parameter tables independently. Deploying the exporter
correction requires a new exporter-run audit before reusing its admission.

The selected corpus gate authenticates current source bodies and compares every
compressed segment and D3D code record with the admitted CLI through a separate
managed checker. A rebuilt CLI changes exporter-run provenance even when game
bytes are unchanged: fresh Shader-only admission can support an independent
projection without renewing an older renderer/collision publication. The WebUI
projection binds that current Shader analysis to an existing Material artifact
only when physical identity, Shader raw hash and Material artifact hash agree.
Its keyword-superset candidates allow additional engine/global keywords and
remain `conditional`; unknown stored valid keywords prevent a shortlist.
Runtime variant selection, pass execution and effective resource bindings remain
`unresolved`, so these declarations do not justify game-equivalent shading.

[`shader/materials.py`](../../scripts/game_data/shader/materials.py) preserves
explicit numeric Material overrides separately from Shader declaration defaults.
It counts matching resource names and named constant-buffer fields within each
conditional LOD/pass cohort, retaining every stored field-offset alternative.
Repeated named tables do not establish instruction use or effective upload;
missing parameter layouts stay counted, and unrecognized keywords still prevent
candidate selection. Texture fallback names remain declarations, not fabricated
decoded images. This is the same separation between source transport and native
application used by the reconstruction lab's material schemas and unavailable
shader paths; those actor-specific conclusions do not transfer to these prefabs.

[`shader/instruction_corpus.py`](../../scripts/game_data/shader/instruction_corpus.py)
adds token-framed native DXBC disassembly through the explicitly selected Windows
system compiler. The checked stored packed-slot lanes are the high byte for VS
and the next byte for PS. An unused stage slot remains unused. Structured-buffer
descriptors additionally distinguish SRV/UAV slots with the stored writable bit;
their executable declarations must have the corresponding structured shape.
These joins prove compiled register references, not the native engine's binding
calls. Scalar/vector field references, anonymous static byte offsets and dynamic
indices stay separate. Complete register joins do not mean complete field names.
Supported operand forms respect destination masks and source swizzles; other
forms retain conservative possible field references instead of proving a read.
The independent lane-aware output reader is conservative and limited to supported
straight-line instructions; control flow and unsupported operations fail closed.
Disassembly preserves the other instructions for later analysis.

For the minimal stored keyword-superset Lit candidate used to study the lifter,
the RGB target reads base, normal, detail and mask textures. Its mask colour
operations blend B, then G, then R, using separate authored colours/weights;
UV0 and UV1 enter separately. Detail colour includes camera-dependent falloff.
Conditionally substituting the stored `_DetailMode` value of one cancels that
colour weight for finite operands, but does not remove detail normal/PBR use.
This is an instruction/source-value observation, not a proof of the live upload,
selected variant, sampled mip, colour transport or deferred lighting. It does
not justify a game-faithful base-texture/tint preview.

[`shader/capture_corpus.py`](../../scripts/game_data/shader/capture_corpus.py)
re-admits stored Shader bodies before comparing saved shader archive bytes and
observed draw identities. Creation/registration is distinct from a draw. Captured
constant prefixes must cover the declared span and fit the bound range;
program equality cannot identify a source Material. The separate compressed
texture comparer uses immutable, hash-checked stored preview inputs and exact
complete mip tails. A same-draw payload additionally requires matching copy
phase, call/Present and bound object/view; a frame-wide draw-local flag alone is
insufficient. The retained reconstruction-lab packets provide shared-program
examples but no texture-content join for this preview selection. The studied
lifter candidate cohort has no retained draw. Effective variant, constants,
SRV formats/mip ranges, samplers and source ownership therefore still require
one selected asset's graphics draw operands before advancing appearance claims.

Fresh selected Mesh-body admission also supports an independent UV1 projection:
the page publisher first reproduces the existing neutral UV0 OBJ byte-for-byte
from those admitted buffers, then changes only texture coordinates. This proves
a stored-channel view against an immutable published artifact without promoting
stored UV-set indices to a live shader route or renewing older renderer gates.

[`unity_render_resources.py`](../../scripts/game_data/unity_render_resources.py)
uses the referring directory's actual ordered external table to join raw
MeshFilter and material slot pointers to a unique physical CAB/object in the
admitted source selection. CABMaps only locate additional candidate Bundle spans:
current VFS hashes, actual parsed CAB names, complete object directories and raw
body checks still precede ownership. Missing directories, objects absent from a
complete selected directory, unselected bodies and physical ambiguity remain
distinct. LOD memberships use actual LODGroup renderer PPtrs and reciprocal
prefab hierarchies; filename suffixes cannot select a level. Mathematical stored
LOD assemblies are useful recovery views but do not prove camera-selected LOD,
additional vertex-stream application, deformation, material appearance or world
instances. Static-batch parts whose transform/range route is unproved remain
counted as excluded instead of receiving a guessed transform.

The stored model-to-collider join also requires the native-gated Model path
hash, the manifest's unique asset path and logical Bundle, the active physical
Bundle identity, and that declared prefab root. It preserves Model placement
and prefab-local collider matrix separately. Runtime registration matrices,
instantiated GameObjects, parenting, animation and enabled state need the
bounded capture described in the DynamicStreaming topic; more static owner
coverage cannot establish those live facts.

For this selected prefab lane, complete directory/body admission closes the
stored Mesh, material, shader and texture reference chain without a live capture.
The remaining placement witness must connect the source Model identity to its
registration id and selected grid matrix, instantiated root, parent, and later
world transform in the same observed lifetime. Existing physics/query evidence
cannot substitute for an unobserved selected instantiation route. Choose a
scene-loading target and check this route's coverage before requesting gameplay;
an additional solver or crate-breaking sample alone cannot close it. Stored
texture decoding and shader interpretation can still improve offline appearance,
but neither can establish runtime material overrides or camera-selected LOD.

Asset extraction and discovery are strong: the project indexes every asset
kind, resolves many PathID-backed dependencies, and connects authored gameplay
or Story records to asset candidates with explicit provenance. The main gap is
semantic binding. Exporting an object does not prove its live prefab
composition, selected material variant, animation state, effect activation, or
placement time.

The Endminf amber ribbon capture contract in
[`endminf_amber_trail_capture.json`](../../scripts/game_data/contracts/endminf_amber_trail_capture.json)
authenticates current M46 source shader variants, sampled texture identities,
material buffer layout and selected native inputs. Fresh installed-carrier
extraction corrected obsolete pixel programs. The current plain SRP pair also
renders trails: `_USE_TRAIL` is diagnostic, not a renderer identity. Shader
prefixes and texture descriptors only admit candidates; material identity
requires full archived shader, texture and material byte joins. Material byte
508 is `_BlendTint.a`, not the legacy `_UseBlend` property. Stored tint RGB is
sRGB; uploaded constants carry Unity's linear conversion, with unchanged alpha.

Retained M46 indexed billboards have zero referenced vertex RGBA and do not
change colour; the first dormant owner replays byte-for-byte. The visible
ribbons instead use non-indexed `DrawInstanced` triangle strips. The corrected
lane preserves the real vertex/instance starts, each input-layout-consumed IA
slot, full constants, three sampled textures, fixed state and each owner's
preceding colour/depth. A bound index buffer is not an input to that call.
The complete strip packet joins all M46 source inputs and has positive
referenced alpha and changed colour. Each of its three retail owners replays
on retained inputs with zero differing packed colour pixels. Shared material
identity alone did not establish this renderer contribution; exact replay did.

The reconstruction exposed two transport errors. Unity 6's active-colour-space
trail baking darkened vertex RGB compared with the retained retail bytes;
the lab runtime corrects that transport while preserving the authored flag.
Retail sampling uses bilinear Repeat for main/flow and Clamp for colour.
The earlier reconstruction used Clamp and Mirror on those two roles. The
material-specific recovered sampler tuple corrects this and materially reduces
the proven entrance-peak error. A stale lab flow image also bound at the wrong
size. The reusable native-texture builder and Unity importer now gate on the
selected native inputs and current source payload, preserve BC7 bytes and bind
the current single-mip flow. GPU inspection proves its byte join, but that
replacement did not change the sampled image metric. Do not infer an image
cause merely from a corrected descriptor.

Ribbon geometry and timing remain open after these fixes. Wall time since
`CharEffect.Play` and global shader time do not establish particle simulation
age. The capture observer now queries the already authenticated root's
`ParticleSystem.time`, count and playing state beside exact-owner Animator
state reads, on the original Play thread. It revalidates particle/GameObject
instance identities, retains its native query interval and fails closed on
missing APIs, invalid state or identity changes. This is a direct root clock;
the child trail clock remains an unresolved join. The verifier reports native
root-clock brackets without assigning child ages or fitting simulation phase. The new packet provides valid brackets for every
retained strip and all three retail replays remain exact. A body-clock
comparison, conditional on supplied owner mapping and native stage origin,
finds matching strip topology after removing only complete duplicate endpoint
records, byte-identical colour and sub-millimetre positional differences.
This constrains geometry without promoting the root clock to child identity.

GPU payload inspection verifies every mip of all three sampled textures.
A separate pixel-shader substitution keeps retail vertex outputs, geometry,
textures and preceding colour/depth intact. Its unchanged retail-shader
translation is exact; the corrected lab pixel shader differs only by packed
colour rounding at a few pixels. That test excludes lab vertex UV transforms
and downstream composition, which remain independent boundaries.

The shared Character Info refraction effect has a separate update-history
boundary. Its child uses the authored fixed seed, but equal seed and final
particle age do not guarantee equal geometry: variable update intervals can
change integration, custom-data evaluation and unsorted particle order. Layer
ablation assigns the largest early strip residual to `CharEffect/trail`, not
the background portrait. Replaying retained Animator Tick intervals at the
same final pose time materially improves that frame and nearby controls.
The lab's reusable cadence builder validates consecutive observations and
stable root/state/thread identity, preserves the existing endpoint tolerance,
and retains an explicit diagnostic boundary. This supports a cadence cause
without fitting the source seed, delay or material, and does not turn a root
clock into a proved child clock. See lab finding 959 and its maintained
`tools/build_endminf_capture_cadence.py` / `tools/scene_video_join.py` consumers.

Shared-strip packet coverage must be checked at the resource-owner level:
a shader archive or draw-census match does not prove its geometry was copied.
The older dedicated packets constrain pixel math but do not authenticate the
later phase now under investigation. The reviewed
`scripts/game_data/contracts/endminf_shared_strip_capture.json` drives two
phase windows and selected build/shader/mask gates for saved packet evidence.
Admission requires same-Play root-clock brackets, complete consumed inputs,
explicit MRT/depth before and after each owner, and changed colour. Its native replay and source
material-constant join are subsequent checks; direct root time still cannot
be promoted to child particle age. The shared root is reused across character
pages: its name, instance identity and successful Play alone do not identify
an Endminf visit. The first live two-phase packet was fully retained and replayed
exactly but preceded all Endminf Ticks, so it failed the visit join. The shared
profile now publishes the original Play timestamp only after an authenticated
Endminf entrance Tick with the same-thread, revalidated root. Tests cover other
pages first, root recycling, notification retry, deduplication and hook epochs.
Target-visit validation still needs the corrected capture in the lab's queue.

Every exported Unity type is already in a decoded or standard format:
AnimationClip as YAML with its curves and keyframes; Animator, AnimatorController,
AnimatorOverrideController, PlayableDirector, Material, MonoBehaviour and
TextAsset as JSON; Mesh as FBX; Texture2D as images; Sprite as crop documents.
No binary framing is left to recover here, which is why MonoBehaviour
*semantics*, not parsing, is what this file records as open.

Binary FBX normalization is owned by `scripts/game_data/fbx_normalize.py` and
shared by the Unity store and Updates comparison. It removes exporter-generated
timestamps and identities while preserving byte lengths and node offsets;
normalized equality is an exported-content comparison, not original Unity
object identity. Node ends must advance within their parent and property blocks
must consume their declared bounds. Unsupported, truncated or malformed trees
return their original bytes, so a corrupt offset cannot hang normalization or
produce a partially normalized comparison.

An apparent missing FBX part requires a geometry comparison before an export
repair. The Ardelia sheep prefab's renderer and LOD pointers account for all
exported LOD meshes, and an independent complete type-tree/body decode of the
referenced Mesh objects matched their FBX vertex coordinates and triangle
indices exactly after X reflection and winding reversal. The horns are part
of those meshes. A weapon-style mesh name is not evidence of an unrelated
mesh or absent body. Its bright emission obscures horn detail in the Assets
preview; the owning display policy is in `memory/webui/assets.md`. This
selected result proves neither other Animator exports complete nor the
game's final shader/lighting appearance.

The broader Animator audit compares complete generic source GameObject,
Transform, MeshFilter and renderer declarations with exported FBX geometry
attachments. Hierarchy joins require reciprocal PPtrs, and external Mesh
identity retains the referring CAB, external slot and target PathID. A non-null
unresolved Mesh reference is an export gap, not proof that the prefab is empty.
`animator_coverage.py` owns that comparison; `fbx_inventory.py` inventories
stored FBX nodes without inflating geometry arrays. Count equality proves only
attachment coverage, not vertex, skin, material or runtime equivalence.

Three exporter failure modes are independently established. Dependencies can
live in the other installed VFS layer, in another bundle offset of the same
physical chunk, or in the selected player's loose built-in Resources files.
The selected-layer CAB map remains authoritative; the other map supplies only
absent names. Model conversion explicitly loads available built-in resource
files and binds their bytes into model cache signatures and auxiliary input
freshness. Explicit dependencies bypass source-object filters but do not become
independent export targets. Root-offset filtering narrows initial selection,
never the transitive dependency closure.

Separately, sibling Transform names need not be unique. Matching a renderer's
mesh to an FBX frame by its string hierarchy path can replace one sibling's
geometry or attach a ghost mesh to an unrendered sibling. Converted meshes now
retain their exact ImportedFrame identity; legacy producers without that identity
retain path lookup. This corrects renderer attachment and does not establish a
new animation, morph or bone binding rule. Missing parsed Mesh targets warn with
their referring source and exact pointer identity. Remaining door definitions
reference a CAB not located in either current layer index; preserve their
partial/empty exports rather than manufacture geometry from similar names.
The saved previous export also lacks that CAB in its layer indexes and lacks
the referenced Mesh PathIDs, so it supplies no archived target for this gap.

The same reader supplies Assets' separate `fbx_content_fingerprint`: a
conditional comparison excluding document URLs naming the current export and
a root Model connected to scene id zero whose label matches the export stem.
The Assets grouping policy also excludes non-bone Null instance labels,
Model local/geometric transforms and pivots, preferred joint angles, PoseNode
matrices and Cluster Transform/TransformLink/TransformAssociateModel matrices.
Cluster-linked Null bones retain their labels. Matrix dimensions and graph
connections remain checked; geometry, material/texture records, mesh/bone
names, hierarchy, skin indices/weights, animation and remaining properties
participate. Strict framing failures withhold the fingerprint. Bind matrices
encode the mesh/bone relationship at skin attachment and can affect
deformation; ignoring them is an explicit pose-insensitive grouping policy,
not a proof of equivalent deformation. No original file or full hash is
rewritten, and grouping establishes neither Unity identity nor runtime use.
The reader returns a second, pose-preserving fingerprint for Assets' `fv`:
it excludes the same export/instance labels but retains transform, pose and
bind values. Matrix arrays are decoded and checked for exact typed dimensions
before hashing, so compressed and uncompressed representations of the same
matrix agree. This distinguishes pose/bind variants within one `fc` resource
group without calling name/path aliases different models.

## Evidence order

Prefer:

1. authored asset/prefab path or direct table key;
2. source root plus PathID/PPtr;
3. exported prefab/component dependency;
4. material-to-texture/shader reference;
5. exact controller, clip, effect, audio, or video consumer;
6. stable normalized identity;
7. labeled name/token similarity.

Preserve source roots, PathIDs, LOD/state suffixes, material slots, texture
roles, and evidence kind. Never treat a global PathID or similar filename as a
unique binding; keep bindings at `(source root, CAB, PathID)`.

## Bundle identity and dependency joins

Each join below is a stored container relationship; none establishes Unity
object ownership, load order, or runtime use. The gates and their full readings
are `scripts/game_data/cabmap.py`, `bundle_cab_dependency_corpus.py`,
`bundle_cab_exceptions.py` and `bundle_external_identity_corpus.py`; the
manifest fields are proved by `scripts/game_data/contracts/bundle_manifest_native.json`.
Per-build counts and source hashes are in `reports/animestudio/`.

- **Container location is exact.** The VFS outer ledger verifies each selected
  logical Bundle's bytes and the inner ledger its Unity structure; joining the
  Persistent CABMap's source root, chunk path and offset to those spans gives
  every added or changed Bundle file one named CAB.
- **An AssetMap row is source containment, not an object check.** Some new
  bundles have no AssetMap row although their CABMap offsets and inner
  structure verify: an AssetMap coverage gap, never an empty container. Select
  StreamingAssets fallback rows by exact source chunk **and offset
  containment** in a verified current Bundle span; chunk membership alone
  cannot promote the fallback AssetMap to current overlay evidence.
- **Path/physical-Bundle disagreements are dependency placements.** Every
  Persistent disagreement and nearly every StreamingAssets one places the
  physical Bundle in the path's listed Bundle's `directDependencies`, with the
  reciprocal reverse entry.
- **The CAB graph matches the manifest.** Every projected external CAB is in
  the manifest direct list (plus a small manifest-only residual that the native
  loaders can consume, cause unproved); the reverse list is its inverse and
  `dependencies` its transitive closure. Unselected CAB targets stay unresolved.
- **`unity default resources` is an authored serialized identity**: an indexed
  pointer through that external reaches the `Capsule` Mesh in the exact-name
  installed Resources file. A second, CAB-shaped external stays unlocated. The
  resolver binding still needs a native or live trace.
- **AssetMap labels from before the ordinal-interning fix are historical.** The
  apparent no-dependency fallback residual was an exporter-label bug:
  `StringCache.Get` in AnimeStudio's `AssetMap.cs` interned by CRC32 alone, so a
  same-CRC path could replace the authored key; every corrected key (the
  Bundle's own `AssetBundle.m_Container` key) maps to that Bundle in both
  manifests. A smaller UI subset's old labels have a *different* CRC from the
  raw keys, so their mislabel mechanism remains open.
- **The no-AssetMap group is parse-only classes.** A ledger-matched dump and an
  opt-in metadata map agree on every `(logical file, CAB, type, PathID)`: mostly
  scene bundles (`AssetBundle`, `GameObject`, `Transform`, `PlayableDirector`),
  the rest controllers or avatars, each `AssetBundle` holding one authored
  `m_Container` path (level sequences, cutscene transitions, dialog timelines,
  UI model controllers, one avatar). All six classes are parse-only in the
  normal CLI configuration, so `AssetsHelper.BuildAssetMap` never emits them:
  that explains the gap without claiming empty bundles or ruling out others.

## Refresh

```bat
.\export.bat assets --from-game
.\export.bat --from-game
.\export.bat debug --from-game
python -m scripts.webui.assets.build_assets
python tools\endfield_source_graph.py build
```

A page run exports only the Unity classes its build tasks read
(`scripts/webui/pages.py`); `debug` exports every class. Primary outputs:
`<export root>/game/{Unity.sqlite,Unity/<Type>/,Audio/}`,
`webui/data/assets/{index,gameplay_refs,story_media,videos}.json`,
`webui/data/lang/<LANG>/audio/{index,events,media}.json`,
`webui/data/lang/<LANG>/gameplay/sound_effects.json`, `reports/assets/` and
`reports/source_graph/`.

## MonoBehaviour: from anonymous objects to named fields

Every MonoBehaviour decodes against an exact serialized TypeTree, but the export
carries only an anonymous `scriptPathId`: `m_Script` points into a MonoScript CAB
outside the export scope. The `scripts/game_data/monobehaviour/` modules close
that in steps, each measured; their docstrings hold the full rules and the
commands are in `scripts/README.md`.

| Module | Establishes | Does not establish |
| --- | --- | --- |
| `census.py` | objects sharing a `scriptPathId` share one layout; the corpus collapses to a few hundred classes | any name |
| `monoscript_catalog.py` | `scriptPathId -> class` from the one MonoScript CAB every `m_Script` reaches | what an instance owns |
| `script_names.py` | an independent layout-to-IL2CPP-class check | a class that serializes nothing, or which subclass of a field-contributing base |
| `field_semantics.py` | per field: declared TypeTree type beside observed occupancy, and PPtr tiers `exact`/`container_only`/`contradicted`/`unresolved` | when a class runs, or that a filled reference is reached |
| `table_keys.py` | string fields whose values are keys of an exported Table | that a consumer reads the field as a key |

A named class is an exact identity for the *script*, and a field row describes a
layout and its occupancy; ownership and runtime use still follow the evidence
order. Conclusions worth carrying:

- **Resolution.** PathIDs are measured unique across this export, and no CABMap
  prediction is contradicted where the target is exported. Most references are
  `container_only` (their GameObject, Transform or MonoScript targets are never
  exported); every filled reference field names a container through the
  ordered-dependency rule ([`containers_cabmap.md`](containers_cabmap.md)), with
  no fallback to a global PathID match. A field null in every object, or
  holding one value in every instance (about a third of all fields), records an
  authored default, not configuration.
- **Material links are uncheckable.** Material, TextAsset and
  AnimatorOverrideController carry no provenance, so Material texture links rest
  on a global PathID match the export cannot check
  ([`extraction_pipeline.md`](extraction_pipeline.md) owns the exporter gap).
- **Bindings at scale.** `Beyond.UI.UIImage.imgRefPath` carries authored asset
  paths (`Assets/Beyond/Arts/UI/Sprites/...`), the first rung of the evidence
  order, and its `m_Sprite` is filled in most objects and names its container.
  Timeline clip fields are the animation binding at scale:
  `AnimationPlayableAsset.m_Clip` is filled in nearly every object and
  `DialogNPCMorphPlayableAsset.m_Clip` in all. The `autoBindingPath` family
  (`DialogSkeletalMorphTrack`, `DialogMuteAutoBlinkTrack`, `DialogLipSyncTrack`)
  is a scene-hierarchy binding that names the character prefab and its
  `FacialMorphCtrlGO`, and `CutsceneRootComponent._director` resolves to a
  `PlayableDirector` at the exact tier in every object.
- **Table keys.** Numeric keys are refused outright, and a `key_of` needs every
  observed value in one table (`UIStateController.states[].stateName` coincides
  with a factory table on one value of 61 and is not a key field). Story's
  strongest bindings: `DialogLipSyncPlayableAsset._trunkId` and
  `DialogTrunkPlayableAsset._trunkId` are `DialogTextTable` keys,
  `DialogOptionPlayableAsset.options[]._optionId` a `DialogOptionTable` key,
  and `UIButton.hintTextId` a `TextTable` key, each over its full value sample.
  Grade a partial field by its best table's coverage, not by "in another table
  versus in none": only a dominant table (`mostly_key_of`) makes exceptions
  worth chasing. `UIText._textId`'s are mostly `PH_*` placeholders;
  `SubtitlePlayableAsset._textId`'s are cutscene and FMV subtitle ids that
  resolve nowhere, a Story finding owned by
  [`../webui/story_recovery.md`](../webui/story_recovery.md).

## Controllers and Sprites

`m_Controller` is structural, not an opaque blob: layers, state machines, state
and transition constants, blend-tree nodes, parameter ids and `m_TOSData`
transform paths all decode, so the controller-to-clip chain a character render
needs closes from the export alone, at the exact-serialized-object tier. For
example `P_actor_endminf_ui_overview_01` is one layer, one state machine and
one entry-selected state playing `A_actor_endminf_ui_overview_02`, a 60 fps
uncompressed clip with position, rotation and scale curves, and the
`ui_overview_start`/`_loop`/`_to_*` clips the lab's targets name all exist.
Runtime state selection is not observed.

A Sprite is exported as a crop of its Texture2D (`endfield.sprite-crop.v1`)
that reproduces AnimeStudio's image pixel for pixel; the crop steps, evidence
and texture PPtr join are in `scripts/game_data/sprite_crops.py`. Name matching
is not identity.

## Current strengths

- WebUI asset and Story-media indexes, renderable asset-entity grouping,
  material/texture/shader/controller/animation/audio/video links, exact
  character post-model enumeration and baseline prefabs, and selected static
  world placements and gameplay/entity associations.
- Gameplay-to-image/model links and playable Wwise-event media candidates for
  projectiles, character skills, and bounded enemy ownership; debug-only audio
  semantics keep Event identity, media id, and each physical
  `(storageRoot, relativePath)` occurrence separate.
- `chen` and `chenpast` are separate identities (`P_actor_chen_*` versus the
  independent `S_npc_major_chenpast_*` mesh family, with no shared model
  PathID), so folding them is a display-layer error.
  `webui/overrides/character_merges.json` is applied in the browser, never by a
  builder, so a merge there overrides this for every reader while generated
  data stays correct and the contradiction is invisible in the exported JSON.
- NPC CPU-animation templates have a native-gated path rule
  (`npc_animation_template_native`) joined to effective source/CAB/PathID and
  declared base and blend-tree clips; a validMontages tag describes authored
  hierarchy, not runtime montage selection or Character Info ownership.

## Remaining gaps

- Integer fields that are table ids cannot be identified from values alone: a
  numeric key belongs to one table only 0.5% of the time. Naming them needs a
  consumer, not a wider join.
- The `mostly_key_of` rows are the open list: fields that are a table's key
  apart from a few ids the tables do not hold. Each remainder is either a
  second key space or content that does not ship; the report does not choose.
- **How much is unexplained is a range; quote the range, not the floor.** Of
  the game-specific named classes, 382 (295,845 objects) have no
  class-specific signal when any non-null reference counts; requiring a
  reference to land on something named (a named target class or an exported
  asset type) raises it to 662 classes (331,986 objects), 71% of the set.
  `Beyond.UI.UIActionKeyHint` has thirteen filled references and none lands on
  a name. Three rules decide the count and must not be relaxed on re-measure:
  the four universal fields (`m_GameObject`, `m_Enabled`, `m_Script`,
  `m_Name`) are excluded first; public engine namespaces are excluded by
  prefix, so game namespaces such as `ScriptAnimation.*` stay in; and the
  unnamed-script class stays in. A Table-key or path-shaped string field also
  counts as signal.
- Which classes a page actually consumes (a question about consumers, not
  layouts); exact runtime prefab assembly, entity-to-renderable ownership, and
  modular NPC and VFX composition; world visibility/spawn policy.
- Material keyword/pass/queue selection and runtime overrides; native texture
  descriptors and mip payloads outside validated families.
- `InitChunkData` proves entity ids, names and matrices but currently exposes no
  prefab Source+PathID/hash field. The Map page's generic entity-name to Mesh
  family join therefore remains a presentation candidate, even if the Mesh
  object itself has an exact AssetMap source/offset/PathID. A current example
  is a world instance named `P_prop_com_plane+1_001_01` whose selected Mesh
  object is cataloged under a dialog-timeline prefab: the shared family name
  alone cannot establish that the world instance uses that prefab or Mesh.
  A targeted parse of that dialog actor prefab did recover its AssetBundle
  root GameObject and reciprocal Transform hierarchy, with direct MeshFilter
  PPtrs resolving through the ordered CABMap dependency to the candidate Mesh.
  That closes prefab-to-Mesh identity inside the actor prefab, but no serialized
  source identity links the streamed entity to this prefab. The Unity object
  store contains AssetBundle documents for the chain, while its published class
  set has no GameObject, Transform, MeshFilter, or MeshRenderer documents;
  those built-in objects required a targeted installed-bundle parse. A runtime
  observation from the streamed entity id to a prefab resource path or root
  source CAB+PathID would close the remaining selection gap.
  Current runtime capture profiles do not observe this pair. The reviewed
  Streaming native rows remain anonymous at the relevant edge, so hooking a
  nearby scene read and correlating by name, timestamp or position would not
  establish ownership. A capture hook needs a validated same-call entity id
  and selected prefab identity, authenticated against the installed native
  inputs and emitted with a bounded completeness receipt.
  Only the separate level/HLOD/grid/cluster hash contract closes HLOD Mesh
  identity; generic objects still need a streamed entity-to-prefab selection
  relation or a direct entity-to-renderer/Mesh runtime observation.
  A bounded current-build native probe rejects the generic
  `FlatBufferConvertContextV2::ConvertAssetFromImpl_Injected` internal call as
  that Map hook: it takes a conversion context and property key, reads the
  context's packed property table, and returns a Unity object pointer. A
  separate named getter reads the context's entity-name string, but the
  reviewed native path does not bind the Init row's ID/name column, a prefab
  root, and a source CAB+PathID/resource path at either call boundary. The
  managed wrapper's one literal direct caller does not supply the missing
  identity pair; other dispatch routes remain unexcluded. A checked runtime
  entity-construction caller/selection ABI is still needed before a dedicated
  capture profile can be built or a game session requested.
  A further selected-build probe of the Init group branch found an ID-keyed
  runtime map: each slot-6 numeric ID can be paired with an eight-byte value
  from a per-group runtime vector. That value's meaning is anonymous, and the
  conditional branch carries no prefab or renderer source identity. A bounded
  follow-up traced the first selected new-record consumer: the second root's
  field-3 ID is used to look up that map, the value is passed to a scope
  setup and copied into an anonymous child record. The scope puts the first
  root's selected row field-3 table and field-0 string into a conversion
  context, then forwards the map value to a dynamic callback. The selected
  group loader constructs the value as a 32-bit descriptor-slot index plus
  a 32-bit counter, rather than a Unity object pointer. The selected default
  callback uses the low 32 bits to index an anonymous context table and then
  select a 576-byte group row. The immediate helpers use the row's bit masks,
  stride and data pointer to resolve anonymous fields. The callback takes up
  to three eight-byte field values, interns each nonzero value as an opaque
  key, and appends 24-byte external-asset request records containing the
  original key, a kind value, and its local index. A named native conversion
  call appends the same record shape. A checked consumer of the matching native
  context field walks a 24-byte request vector and deduplicates its opaque
  keys into another local table; this consumer does not resolve a source path,
  Unity object, or CAB+PathID. Its execution for the target scene is unproved.
  The selected manager constructor receives the group table pointer from its
  owner and stores both a copy of that pointer and the address of the owner's
  pointer field. Thus the group-loader table and the callback context's first
  pointer alias at construction. A later mutation of that owner field or
  either manager field is not excluded by this static trace, and there is no
  live pointer receipt. In the exported target pair, both roots carry the same entity
  ID at the selected ordinal;
  this remains a serialized pair witness, not a runtime load receipt. The
  selected callback's runtime override state and the external-asset request
  consumer have no proven edge to a prefab source identity. A hook at the
  current ID lookup or field-intern call would record only an ID plus opaque
  numeric state; it is not yet a useful prefab-selection capture. A dedicated
  capture hook or WebUI join still needs that keyed resource-selection edge.
- The selected portrait clock observer contract is maintained at
  `scripts/game_data/contracts/endminf_portrait_clock_capture.json`. Native
  metadata proves the PlayIn/SampleClip argument ABIs and wrapper field types;
  the scene-video runtime observes the original calls on their invoking thread,
  with identities, unscaled-time queries and render clocks. Retained direct
  call arguments remain separate from a visible portrait/source-curve join.
  Validate a reader's consumed unpatched APIs independently from method
  entries already replaced by another installed observer. Rechecking the full
  Animator entry set after Animator installation caused the first portrait
  startup failure; its object-reader gate is now separate, with a regression
  that retains rejection of changed reader bytes.
  The observed 1.17 px portrait displacement under an approximate visit lead
  improves with the earlier measured lead, but the remaining peak is not
  explained by that timing control. The shader's native 8-bit alpha rounding
  is now reproduced; no global fitted UI clock is promoted.
- Animation/effect activation and controller execution; broader exact
  audio/video trigger ownership, runtime-selected Wwise switch/random media,
  and stronger inferred skill/enemy sound ownership.

The goal is an evidence-first catalog, not a claim that every gameplay id has
one uniquely reconstructed renderable prefab.

The live portrait observer now separates repeated PlayIn calls on the same
wrapper into their own QPC-bounded visits. Forced reset/end samples alone do
not prove natural progression. Retained SampleClip arguments joined to source
curves and portrait vertices corroborate position and byte alpha; multiple
updates before a draw remain ambiguous. The unscaled-time query is separate
from effective tween elapsed time. A following Animator read shared by two
sync draws gives conditional body age, even with a small interpolation residual.
Use the retained prior Tick control before attributing a large image error to
animation. The remaining early portrait residual survives matching UVs, alpha
and subpixel corner placement. Scene-video retains portrait VS constants but
omits its PS constants and sampled depth. The accepted early material packet
supplies both: native replay and portrait fragment/texture substitutions are
exact; matched lab GPU depth changes only 85 output pixels. This constrains
clipping at that packet, not every animation phase or later composition.
The bounded front-camera profile is reviewed in
`scripts/game_data/contracts/endminf_early_coat_portrait_capture.json`; require
full native shader, consumed IA/CB/SRV payloads and draw-local colour copies
before replaying that question. No global visit lead or source curve change
is justified by these diagnostics.

Diff-layer ablations identify the early shared refraction strips separately
from the portrait. Replaying retained variable update intervals at the same
endpoint improves those strips without changing source particle parameters;
it remains a capture diagnostic, not proof of a child-clock join. The accepted two-phase strip packet separates a burst-age workaround from
continuous emission: delaying the entire lab system aligned the initial burst
but moved later births. Keeping the retained root clock and deferring only the
time-zero bursts reproduces particle order, GPU colour/UV and custom data in
both phases, with roughly 0.05 mm vertex RMS. Native draws replay exactly;
geometry substitution leaves small floating-point/rasterization error. This is
a retained-clock correction, not a universal child-clock or UI-event rule. The
shared-strip capture request is closed. The remaining
fabric-detail mismatch survives strip removal. Matching native shader identity
and global mip bias cannot prove matching sampled texture levels, sampler LOD,
material constants or temporal history. Require the early coat packet's full
fragment inputs before changing texture imports or normal strength. The accepted
packet's complete 512-square diffuse/normal/packed chains match source mip tails;
the lab intentionally keeps its 2048-square textures. Draw-aligned Cloth01
controls show close broad highlights and shadows, with little improvement from
substituting retail's screen-shadow mask. Do not fit lighting strength from the
fine-detail residual or generalize this owner to hair and stones. The portrait
uses point/clamp depth sampling. Its actual bound depth must be inspected;
the lab's separate DOF depth readback is not a substitute for that identity.

The UI export contains separate `reading_`/`read_` illustrations alongside inventory icons. Full suffix equality after removing an authored `item_mission_`, `item_quest_` or `item_` prefix can supply a conditional display association for quest items; it does not establish a native reading consumer or mission ownership. `media_resolver.quest_reading_image_tokens` centralizes this naming rule, and consumers must require exact complete asset basenames. Original Texture2D images may be larger and wider than their Sprite crops, so reading illustration selection ranks source pixel dimensions before shape.
`media_resolver.quest_inventory_image_tokens` supplies conditional quest display names: the exact item ID first, then the complete unnumbered basename when only a final letter-only word has variant digits. Mission IDs and underscore-separated record numbers remain intact.

Weapon entity IDs do not establish icon ownership. `ItemTable.iconId` is the
explicit inventory image binding and may cross-bind differently named weapon
assets; `WeaponBasicTable.modelPath` can likewise reference another basename.
Gameplay weapon pictures and Story Wiki pictures must follow the authored
inventory icon binding, matching Items, rather than assume ID/basename identity.
