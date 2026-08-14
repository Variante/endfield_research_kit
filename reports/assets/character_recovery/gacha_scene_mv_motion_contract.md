# SceneMV total order and selected-character motion contract

Date: 2026-08-14

Verdict: **SOURCE_CLOSED_CURRENT_BUILD** for the isolated selected-character
CharInfo/VFX scene. The remaining general-world target-1 enumeration and the
lab's source-compatible MRT implementation remain open; no Unity patch is
justified by this evidence.

## Evidence pins

- `GameAssembly.dll` SHA-256:
  `0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE`.
- `UnityPlayer.dll` SHA-256:
  `B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`.
- `global-metadata.dat` SHA-256:
  `90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E`.

The source-backed checker
`scratch/reverse_engineering/scenemv_total_order_recovery/verify_scenemv_total_order.py`
passes with these hashes and verifies native anchors, attachment metadata,
shader outputs, and the serialized total-order report.

## Logical SceneMV resource

`HGRenderPathScene.OnPreRendering` resets `sceneMV` to a null logical handle at
field `+0x1300`. When `HGCamera.enableMV` is true it creates a transient full
scene-resolution 2D texture and stores the new handle. The descriptor is:

- `A2B10G10R10_UNormPack32` (GraphicsFormat value 75);
- Point/Repeat, single-sample, no mip, no random write, `bindTextureMS=false`;
- neutral clear `(0.5, 0.5, 0, 0)` and no fabricated history texture;
- fast-memory descriptor enabled with flags `1` and residency `1.0`.

The logical handle may alias a RenderGraph-pool allocation; the binary proves
the per-call handle lifecycle and descriptor, not a fresh physical GPU
allocation. The camera's current/previous view, projection, non-jittered
projection, and world-position constants are copied by
`HGCamera.UpdateViewConstants`; reset mode seeds previous values from the
incoming frame to avoid invented motion.

## Attachment and retail total order

The default deferred GBuffer binds SceneMV as attachment/target 1 and clears
it to the neutral value. OnePassDeferred clears it in phase 0 and loads it in
phase 1. Forward motion-vector preparation binds the caller-selected target
with Load/Store; it does not clear the attachment.

The recovered `HGRenderPathDefaultDeferred.RenderScene` / scene virtual slots
establish this order:

1. earlier opaque/deferred chain;
2. GBuffer (SceneMV initial owner/clear);
3. ForwardOpaque (opaque CharacterNPR target-1 writers);
4. main ForwardOnly transparent;
5. Distortion;
6. Phase 1: LightShaftApply, Parafin, DepthOfField, MotionBlur;
7. ForwardOnly after DOF;
8. LensFlare;
9. optional HorizontalBlurPreTAAU;
10. Phase 2 post-processing.

The scene stores `sceneColor` at `+0x12e0`, `sceneDepth` at `+0x12f0`, and
`sceneMV` at `+0x1300`. Main ForwardOnly publishes its color before Distortion
reads all three handles; Distortion publishes before post-processing;
MotionBlur publishes before after-DOF ForwardOnly; and that pass publishes
before LensFlare. These are direct native callsite relationships, not inferred
from pass names.

## Selected character producer

ForwardOpaque binds SceneMV as target 1 with Load/Store and executes the
character opaque ECS/render lists in the same MRT owner. Sixteen recovered
Wulfa and Zhuang Fangyi CharacterNPR variants (skin, cloth, hair, and eye;
screen and no-screen forms) declare `SV_Target1`: R/G contain packed motion,
B is `1`, and A is the recovered `0.4` or `0.7` discriminator. Selected VFX
then consume the already-populated attachment; rendering only VFX against a
neutral-cleared target omits the retail opaque producer.

The selected Zhuang piaodai transparent material serializes a constant
Target1 `float4(0, 0, 1, activeMask)` with transparent-motion disabled, so its
exact output bypasses previous-state motion RG. Other motion-enabled routes
consume current/previous non-jittered camera constants and paired current/
previous skin-matrix ranges; SceneMV itself remains current-frame data.

## Boundary and recovery rule

The isolated selected-character pass/attachment/shader-output boundary is
closed. Exhaustive terrain/foliage/vegetation target-1 writer admission,
UnityPlayer's physical skin-buffer swap/reuse schedule, and a compatible
source MRT implementation in the lab remain open. Keep the lab fail-closed:
do not fabricate a history texture or substitute an incompatible motion
format/attachment.

Primary scratch evidence:

- `scratch/reverse_engineering/scenemv_total_order_recovery/`;
- `scratch/reverse_engineering/scenemv_runtime/`;
- `scratch/reverse_engineering/vfx_mrt_source_chain/`.
