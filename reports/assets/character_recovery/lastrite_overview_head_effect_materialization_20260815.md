# Last Rite Overview head-effect materialization

`P_fxui_lastrite_ui_overview_start_01_01` is now the first non-Zhuangfy
Overview effect materialized in the Unity recovery lab from an independently
proven AssetMap prefab container. It preserves 8 hierarchy nodes, 5
ParticleSystem/renderer pairs, one head mesh, and exact EffectSetting timing
(`delay=3.5`, `duration=13.5`, non-looping).

The owning `AnimatorBehaviourPlayEffect` is PathID `-4656349351873182958` in
`chr_0026_lastrite_controller`. Its 768-byte raw object declares eight ordered
`FromOveview` requests. The head request mounts at the unique
`Bip001_HeadNub`; Unity serializes all eight requests, binds only this proven
prefab, and rejects the other seven.

Exact evidence:

- prefab container: `assets/beyond/dynamicassets/gameplay/effects/prefabs/p_fxui_lastrite_ui_overview_start_01_01.prefab`
- VFS object: `98E51B76A48F5BEF8D07BDFD3E4DA7ED.chk`, offset `158108997`
- controller SHA-256: `27F74C7DAFB337F005BEAC50019E0A3DFF2D450870F04021FC602E7E09C33F30`
- behaviour raw SHA-256: `057D10CB448B05904C76A5CBD2BE5660CD01FD3D649188C5530A4EF5335CA656`
- head mesh: `S_fx_lastrite_head901`, PathID `3275334214857909696`
- six materials use `HGRP/Effect/VFXBaseV2`, shader PathID `-1430105248647086886`

The generated contract embeds the mesh and serialized component payloads, so
Unity rebuilding does not depend on scratch files. Exact material
specializations and textures remain open; all six use the ColorMask-0
unavailable shader and stay invisible. Unity 2022.3.62f3 batch validation
passed for both importer and actor binding. This is execution progress, not
retail visual parity.
