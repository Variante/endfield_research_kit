# Li Zhiyan M23 exact-DXBC native draw fixture

This isolated D3D11/WARP tool validates resource creation, explicit binding,
and a controlled 1x1 draw for the exact M23 `HGRP/Effect/VFXBaseV2`
ForwardOnly vertex and fragment programs. It does not integrate with Unity or
claim visual fidelity.

Run from the lab root:

```powershell
.\tools\original_m23_dxbc_exact\build_plugin.ps1
python .\tools\original_m23_dxbc_exact\test_validate_diagnostic.py
```

The default `exact_pair` validator creates the exact VS/PS, the ISGN-derived
136-byte input layout and vertex buffer, separate stage-specific b0..b4
buffers, five SRVs, five samplers, and controlled rasterizer/blend/depth
state. It also creates and binds the VS structured-buffer t0
(`_VertexSkinMatrices`) separately from the PS texture slots. VS and PS
buffers stay separate because their SHEX declarations have different sizes.

The build also runs `diagnostic_vs_exact_ps`: a pinned `diagnostic_vs.hlsl`
compiled with `D3DCompile`, using `SV_VertexID` and emitting the exact 0139 PS
ISGN (`SV_Position`, `TEXCOORD0..7`, including float3 masks). This mode binds
the exact PS and its b0..b4/t0..t4/s0..s4 resources but creates no 0138 VS,
input layout, vertex buffer, or VS structured resource. The source hash and
signature contract are fail-closed report gates.

`diagnostic_vs_exact_ps_named_low` uses the same diagnostic VS and exact PS,
but initializes only source-backed PS `cb4[0..9]` named components from the
M23 material. Unnamed components and `cb4[10..43]` remain zero. The material
hash and generated M23 contract hash are checked from their source files by
`build_plugin.ps1` before compilation; their embedded pins and the serialized
component map are then reported and gated. Synthetic textures remain in use.

The build also runs bounded register-only diagnostics for the 57 high-slot
components read by exact 0139. A single-component probe, an all-active
baseline, a numerical-domain-neutral baseline, and three low-component
overrides all retain the exact PS and report `visual_fidelity_claim=false`.
The high baselines set diagnostic PS `b2[4].x=1` to pass the explicit dither
gate and independently staging-read/hash the synthetic t0 resource. Every
current combination still writes transparent black. This proves only that
the tested inputs are insufficient; it does not name high slots or recover
material values. The build executes and validates every maintained mode.

Two exact-texture modes replace synthetic t0..t4 with the five M23 PNGs joined
by the generated peak contract. The build checks every PNG hash, WIC-decodes
the original dimensions to RGBA8 UNORM without an sRGB transform, and uses a
separately source/compiled-hash-pinned diagnostic VS to sweep UV `[0,1]` over
a 16x16 target. Named-low constants produce 0/256 nonzero pixels. The
numerical-domain-neutral high-slot diagnostic produces 175/256 nonzero pixels
with maximum RGBA `[0,0,0,1]`. This is the first exact-PS alpha activation;
RGB remains unresolved and the diagnostic UV/high-slot inputs are not vertex,
material, or visual fidelity.

The texture VS now labels its TEXCOORD5 particle-color input explicitly as
diagnostic white. With high-neutral constants alone, RGB still remains zero.
The bounded `exact-textures-high-neutral-rgb` mode then sets only PS
`cb1[27].y=1`, the global multiplier selected by the proven low
`cb4[3].x=1`. Exported metadata identifies it as
`ShaderVariablesGlobal._ExposureWithMiscParams.y` at byte offset 436; the
recovered native producer defines it as reciprocal camera exposure, and 1 is
the constructor default and neutral 0-EV value. It produces 175/256
RGB-and-alpha pixels with maximum HDR RGBA
`[0.660757,2.68497,2.79676,1]`. This isolates a real texture/color execution
path. Exact 0138 shows that fragment TEXCOORD5 is VS `o6`, selected between
input COLOR0 and `COLOR0 * (1 - cb3[13])`. Selected-frame vertex color,
attenuation, exposure history, UVs, and neutral high slots remain diagnostic
or runtime-open rather than recovered fidelity values.
All four particle renderers using the exact material serialize custom vertex
streams `[0,1,3,4,5,34]`, including Color, and their start/color-over-lifetime
RGB is white. White RGB is source-backed; selected-frame alpha and `cb3[13]`
are still runtime-open.

All buffers are zero-initialized. Unresolved b4 high-slot semantics are not
inferred. The validator explicitly binds every object, verifies identity with
VSGet*/PSGet*/IAGet*/OMGet* masks, draws three vertices into a controlled 1x1
float RT with triangle-list topology and a 1x1 viewport, and maps a staging
copy. `readback_changed_from_sentinel` is reported
but is not a pass gate; `visual_fidelity_claim` is always false.

## Opt-in Unity bridge

`OriginalM23DxbcUnityBridge.cpp` is linked into the same DLL as the fixture;
the standalone exports and report layout above remain unchanged. Unity calls
`UnityPluginLoad` and `UnityShaderCompilerExtEvent` through the normal native
plugin/compiler-extension ABI. The compiler configuration reserves
`ENDFIELD_ORIGINAL_M23_DXBC_EXACT` and advertises only D3D11 SM5 VS/PS
programs. The bridge is disarmed after plugin load and only arms through
`EndfieldOriginalM23DxbcBridgeSetArmed(1)`.

While armed, a callback must pass the D3D11 platform and exactly-one VS/PS
stage gates before replacement. Unity supplies shell/variant bytecode to this
callback rather than the original retail 0138/0139 bytes, so the bridge does
not make an impossible byte-for-byte input comparison. The reserved keyword
and explicit arm request are the opt-in contract; it claims at most one exact
object per stage per arm cycle, while callbacks before arming and extra stage
objects remain Unity-owned. The bridge retains a separate COM reference for
render-event identity checks, so the stored pointer does not depend on Unity
retaining the compiler output object.

`EndfieldOriginalM23DxbcBridgeGetRenderEventFunc()` returns an arm-aware
render-event callback. Event ID 1 inspects current D3D11 VS/PS and the M23
five-slot constant/resource/sampler masks. Event ID 2 runs the already-proven
exact-pair fixture against the current Unity D3D11 device: it creates
controlled M23 b0..b4/skin/texture/sampler resources, input layout and
triangle, float render target, issues the exact VS/PS draw, staging-reads the
result, and then calls `ClearState()`/`Flush()`. It increments native
execution/draw counters and exposes finite/changed/changed-from-zero output
bits plus four readback floats. Event ID 3 disarms and releases retained
compiler shader COM references on the render thread. Callers should call
`SetArmed(0)`, issue event 3, and only then unload or rearm.

Event IDs 4 and 5 are observation-only callbacks placed immediately before
and after the managed diagnostic `DrawMesh`. They inspect the current D3D11
bindings and attempt to copy VS `b3` through an unbound staging buffer only
when its resource is exactly the recovered 224-byte `cb3[14]`. Missing,
mismatched, or unreadable resources publish no bytes. On Unity 2022.3.62f3 the
callbacks execute, but both boundaries expose no VS `b3`: the draw's internal
bindings are not observable from adjacent plugin events. This maintained
negative result does not weaken the independent exact-shader execution gate.
Capturing a real particle draw therefore requires a draw/API hook or external
graphics capture rather than another adjacent plugin event.

Do not replace the immediate context object's COM vptr to obtain that draw
boundary. A bounded isolated-player experiment shadowed the complete 115-slot
table, intercepted only Draw variants, and filtered by the exact retained
VS/PS objects. Unity crashed inside `Graphics.ExecuteCommandBuffer` before a
report on two storage-lifetime variants. The experiment was removed and the
published plugin rebuilt from the safe observer source.

## Supported DXCap evidence path

Windows Graphics Diagnostics provides a supported D3D11 capture boundary for
the isolated player. For this short player the useful frame is frame 0; later
frames may contain only the shutdown shell. Capture and export the API event
stream with:

```bat
cd unity_endfield_graph_shader_lab\tools\original_m23_dxbc_exact
C:\Windows\System32\DXCap.exe -file <capture.vsglog> -frame 0+1 -terminateonsave -c <player.exe> <player arguments>
C:\Windows\System32\DXCap.exe -p <capture.vsglog> -toXML <capture.xml>
python dxcap_xml_evidence.py <capture.xml> -o <capture.evidence.json>
python test_dxcap_xml_evidence.py
```

`dxcap_xml_evidence.py` accepts both the rootless XML emitted by the installed
Windows SDK and bounded rooted fixtures. It incrementally tracks D3D11 shader,
IA, constant-buffer, resource, sampler, topology, viewport, and target state.
The exact diagnostic candidate requires the known VS/PS bytecode lengths and
the 136-byte IA stride. It never promotes object handles or bytecode lengths
to byte hashes.

The parser recognizes both unique M23 length pairs: blob1277/non-instanced is
VS 10,720 plus PS 8,100 bytes, while blob1956/`SRP_INSTANCING_ON` is VS 11,016
plus PS 8,188 bytes. It tracks the created handles to the draw, still requires
stride 136, and rejects mixed pairs. This classifies a compiled variant
candidate, not actor identity or vertex/constant-buffer contents.

The current isolated capture locates one exact candidate at moment 9748:
`Draw(3,0)`, VS handle 8343, PS handle 8344, IA stride 136, and five VS
constant-buffer handles 8347 through 8351. The XML does not inline vertex- or
constant-buffer contents, so this closes safe draw identification only. It
does not recover the 136-byte source row, the 224-byte VS `cb3[14]`, or retail
particle visibility. Keep `.vsglog`, replay XML, and generated evidence JSON
under `scratch/reverse_engineering/`; they are disposable capture artifacts,
not tracked source contracts.

Event 2 intentionally owns and clears Unity's immediate-context state for the
duration of the isolated diagnostic pass; it is not safe to interleave with a
normal viewer frame. The managed diagnostic gate invokes it only in the
isolated player, which exits immediately; no normal viewer path invokes the
event. The callback does not claim visual fidelity or reuse Unity's transient
post-draw bindings. Arm, shell-input-observed, blocked, failure, cleanup,
binding, draw, readback, and render counters are reset at the arm boundary and
exposed through deterministic bridge getter exports. The build script copies
the linked DLL to the lab's x86_64 Unity plugin folder after the native compile
succeeds.
