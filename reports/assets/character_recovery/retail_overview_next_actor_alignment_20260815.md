# Retail Overview next-actor alignment

Date: 2026-08-15

This report joins video identity and controller-owned effect records without
using visual resemblance to infer ownership.

| actor | retail interval | source-owned acceptance target |
|---|---:|---|
| `chr_0032_lizhiyan` | `38-47 s` | 11 root effects plus `P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub`; teal rectangles, ribbons/trails, glitch, hair and garment motion are frame-level acceptance layers |
| `chr_0028_wulfa` | `48-55 s` | eye, smoke, trail01/02, hit, qiekai, cloak, knife and wind records; cloak trails mount at `clothes_cloak_L_b_09_jnt` and `clothes_cloak_L_c_09_jnt` |
| `chr_0018_dapan` | `283-296 s` | low-VFX regression target with exact bowl, noodle, chopstick and glasses mounts; prevents a global-particle template from being mistaken for actor recovery |

The video supplies timing and appearance acceptance bounds. Controller
`_effects[]` supplies owner and mount evidence. A root effect is not assigned
to an individual pixel layer until its prefab, material, lifetime, and render
path close independently.

Li Zhiyan is the next strongest retail high-energy target; Wulfa is second.
Camille and Last Rite have unambiguous catalog mounts, but only an exact
AssetMap container/object row can promote an individual requested name to a
materialization candidate. Follow-up inspection proves such a standalone row
for Last Rite's head effect; controller scalar repetition alone does not prove
Camille's effect-prefab availability. The video alignment remains stronger for
Li Zhiyan and Wulfa.
