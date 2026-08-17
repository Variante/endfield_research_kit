# Li Zhiyan M23 exact-DXBC creation fixture

This isolated D3D11/WARP tool validates resource creation for the exact M23
`HGRP/Effect/VFXBaseV2` ForwardOnly vertex and fragment programs. It does not
bind resources, issue a draw, integrate with Unity, or claim visual fidelity.

Run from the lab root:

```powershell
.\tools\original_m23_dxbc_exact\build_plugin.ps1
python .\tools\original_m23_dxbc_exact\test_validate_diagnostic.py
```

The validator creates the exact VS/PS, the ISGN-derived 136-byte input layout
and vertex buffer, separate stage-specific b0..b4 buffers, five SRVs, five
samplers, and controlled rasterizer/blend/depth state. VS and PS buffers stay
separate because their SHEX declarations have different sizes.

All buffers are zero-initialized. Unresolved b4 high-slot semantics are not
inferred. Explicit binding, draw execution, GPU readback, and Unity callback
integration are the next recovery boundary.
