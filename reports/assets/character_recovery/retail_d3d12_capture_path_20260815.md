# Retail D3D12 capture path audit

RenderDoc 1.45 is installed at
`tools/RenderDoc_1.45/RenderDoc_1.45_64/renderdoccmd.exe`. Its capture and PID
injection paths cover D3D12 PSOs, root signatures, shaders, descriptors,
resources, MRTs, depth/stencil state, and optional CPU callstacks. The pinned
retail executable and native binary hashes match the selected build.

No successful retail `.rdc` exists yet. The lab auto-capture targets only the
Unity standalone player; the current Frida renderer-list trace does not capture
D3D12 draws, PSOs, descriptors, constant buffers, MRTs, or pixels. Telemetry
cannot replace a draw capture.

Next, attach/inject into a normally launched retail client during a Zhuangfy
Overview effect-active frame. Stop if protection rejects attachment or
terminates the client. Inspect `HGRP/Effect/VFXBaseV2`,
`M_fx_ui_zhuangfy_lightning_901`, ForwardOnly blob 1260/33, both MRTs, and live
descriptor/global state. RenderDoc does not normally expose serialized Unity
PathIDs, so exact attribution still needs a controlled single-renderer
comparison or capture-window correlation.
