# Overview Animator effect coverage

Date: 2026-08-15

The fixed-build controller audit contains 31 playable Overview controllers,
198 referenced behaviour PPtrs, and 165 decoded
`AnimatorBehaviourPlayEffect` records. Those records contain 369 effect
entries and 304 unique effect names.

The existing MonoBehaviour object index contains exact-name rows for 223 of
the 304 names, covering 288 of the 369 entries. This is source-object
availability, not a complete prefab/material/lifetime or pixel-equivalence
claim.

The current Unity lab has three standalone generated Overview effect prefabs:

| effect | renderer gate |
|---|---|
| `P_fxui_zhuangfy_ui_overview_start_01_01` | admitted, `0/19` fail-closed |
| `P_fxui_zhuangfy_ui_overview_start_01_baofa` | `1/19` fail-closed |
| `P_fxui_zhuangfy_ui_overview_start_01_finger_lightning` | admitted, `0/3` fail-closed |

`P_fxui_zhuangfy_ui_overview_start_01_piaodai` is an actor-embedded animated
object and must not be counted as a missing standalone particle prefab.

Of 228 non-root mount entries, 217 resolve to a unique GameObject name in the
generated actor prefab, 11 are ambiguous, and none are missing. The ambiguity
is concentrated in Aurora (`Bip001_R_Foot`), Yvonne (`move_jnt`), and Pograni
(`wep_R`, `wep_L`, `Clavicle`). A bare mount remains fail-closed unless it is
unique; future recovery should prefer the serialized full hierarchy/PPtr when
names collide.

Highest-value source-backed materialization batches are:

1. `camille`: 36 entries, 33 source-backed names, no mount ambiguity.
2. `lastrite`: 17 entries, 16 source-backed names, no mount ambiguity.
3. `pograni`: 15 entries, all source-backed, but 8 ambiguous mounts requiring
   exact hierarchy recovery first.

The census was reproduced from the existing controller audit, the exact
MonoBehaviour object index, and generated actor/effect prefab markers. It did
not run a second broad AnimeStudio export.
