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

All buffers are zero-initialized. Unresolved b4 high-slot semantics are not
inferred. The validator explicitly binds every object, verifies identity with
VSGet*/PSGet*/IAGet*/OMGet* masks, draws three vertices into a controlled 1x1
float RT with triangle-list topology and a 1x1 viewport, and maps a staging
copy. `readback_changed_from_sentinel` is reported
but is not a pass gate; `visual_fidelity_claim` is always false.
