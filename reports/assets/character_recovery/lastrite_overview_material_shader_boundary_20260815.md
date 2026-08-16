# Last Rite Overview material/shader boundary

The six materials used by
`P_fxui_lastrite_ui_overview_start_01_01` are now closed as serialized material
payloads and texture identities, but remain deliberately invisible in Unity.

## Closed evidence

- six exact Material objects, all using `HGRP/Effect/VFXBaseV2` PathID
  `-1430105248647086886`;
- five materials select `_SAMPLE_TEX0 + _SAMPLE_TEX1 + _USE_SOFTBLEND`; one
  selects `_SAMPLE_TEX0 + _USE_SOFTBLEND`;
- both exact compiled ForwardOnly DXBC pairs exist and write `SV_Target` plus
  `SV_Target_1`;
- 12 unique non-null Texture2D PathIDs resolve uniquely through AssetMap;
- all 12 have current converted PNGs whose paths, byte sizes, and SHA-256
  values are pinned in the generated Last Rite contract;
- each material's full serialized payload, texture slot FileID/PathID and ST,
  queue, blend/depth/cull state, floats, colors, and keywords are embedded in
  contract schema v2.

No additional targeted Texture2D extraction is needed for converted pixels.

## Remaining fail-closed boundary

Keyword identity does not close the retail draw. There is no retail D3D12
proof for the selected PSO, descriptors, native BC/mip-chain sampling,
ForwardOnly MRT attachments, scene depth/color handoff, or render-graph
scheduling. Queue 3700 and the head material's mask/dissolve/deferred state are
especially unsafe to reduce to the existing Zhuangfy compatibility shader.

All six generated materials therefore remain on
`Hidden/Endfield/Recovered/VFXUnavailableFailClosed`. The 12 PNGs are evidence
artifacts, not admitted Unity samplers.

## Retail-video observation

The Last Rite slot is `269.25–283.25 s`: transition at `269.25–270.25`, active
entrance at `270.25–273.75`, clean idle/settle at `274.0–282.25`, and the next
transition at `282.5–283.25`. At the available recording resolution, no head,
hand, thigh, or ear particle pass can be independently identified. Visible
content is dominated by animation, cyan hair, black/white costume and weapon
geometry, and gray-white transition haze. This video is therefore a weak
oracle for admitting the recovered head effect; it cannot replace a draw
capture.
