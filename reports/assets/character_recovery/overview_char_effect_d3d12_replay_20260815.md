# Character Info `CharEffect/trail` D3D12 replay diagnostic

Date: 2026-08-15

## Result

The Unity lab now has an isolated Direct3D12 replay diagnostic for the exact
generated Character Info `CharEffect/trail`. It is deliberately classified as
`unity_command_buffer_replay_not_retail_capture`; it does not claim to capture
the retail renderer list or final retail PSO.

The diagnostic instantiates the source-closed prefab, simulates it to `0.125 s`,
binds the recovered SceneColor/SceneMV/depth MRT layout, issues the trail draw,
and GPU-reads both color attachments. The latest run records:

- graphics API `Direct3D12`;
- exact queue `3000`, `_USE_RBOFFSET`, Blend0 `5/10`, Blend1 `3/6`,
  ZTest `4`, ZWrite `0`, Cull `2`;
- root particle system: zero survivors, matching its disabled/null-renderer
  source role;
- trail: `3,572` survivors at the fixed simulation point;
- SceneColor: `B10G11R11_UFloatPack32`, 16,384-byte nonzero readback;
- SceneMV: `A2B10G10R10_UNormPack32`, 16,384-byte nonzero readback;
- both MRT hashes differ from their pre-draw fixtures.

The disposable exact run data is
`unity_endfield_graph_shader_lab/scratch/character_recovery/charinfo_d3d12_capture/diagnostic.json`.
The maintained entry point is
`unity_endfield_graph_shader_lab/run_charinfo_d3d12_capture_diagnostic.bat`.

## Closed boundary

This proves that Unity D3D12 accepts the generated particle payload and the
property-bound VFXRefract material, admits the enabled trail, executes its dual
MRT program, and changes both recovered attachment formats. It also makes the
simulation point, survivor count, material state, descriptors, and readback
hashes machine-auditable rather than relying on a screenshot.

## Remaining retail boundary

The replay uses an isolated CommandBuffer draw and a controlled SceneColor
fixture. It does not prove the retail camera's cull survivors, per-particle
order, RenderStateBlock override, physical render-graph aliases, live global
constant buffer, or final presentation pixels. Those still require a capture
from the same gated retail build or a separately identified equivalent frame.
