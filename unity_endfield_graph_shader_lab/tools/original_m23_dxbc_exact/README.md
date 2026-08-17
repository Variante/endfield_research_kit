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
`cb4[3].x=1`. It produces 175/256 RGB-and-alpha pixels with maximum HDR RGBA
`[0.660757,2.68497,2.79676,1]`. This isolates a real texture/color execution
path, but the white vertex color, global multiplier, UVs, and neutral high
slots remain diagnostic inputs rather than recovered runtime values.

All buffers are zero-initialized. Unresolved b4 high-slot semantics are not
inferred. The validator explicitly binds every object, verifies identity with
VSGet*/PSGet*/IAGet*/OMGet* masks, draws three vertices into a controlled 1x1
float RT with triangle-list topology and a 1x1 viewport, and maps a staging
copy. `readback_changed_from_sentinel` is reported
but is not a pass gate; `visual_fidelity_claim` is always false.
