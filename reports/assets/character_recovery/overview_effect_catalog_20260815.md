# Overview Animator effect coverage

Date: 2026-08-15

The fixed-build controller audit contains 31 playable Overview controllers,
198 referenced behaviour PPtrs, and 165 decoded
`AnimatorBehaviourPlayEffect` records. Those records contain 369 effect
entries and 304 unique effect names.

The existing MonoBehaviour object index repeats 223 of the 304 names in
`.effectName` scalar rows, covering 288 of the 369 entries. This is controller
string indexing only: it does **not** prove an independently serialized effect
prefab or asset. Independent existence must come from an exact AssetMap
container/object row. The earlier `source-backed` label for this count was
incorrect and is superseded by this boundary.

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

The original name-count heuristic ranked these investigation batches:

1. `camille`: 36 entries and no mount ambiguity.
2. `lastrite`: 17 entries and no mount ambiguity.
3. `pograni`: 15 entries, but 8 ambiguous mounts requiring
   exact hierarchy recovery first.

This ranking is a controller workload heuristic, not an asset-availability
ranking. Follow-up AssetMap inspection independently proves
`P_fxui_lastrite_ui_overview_start_01_01` has its own effect-prefab container;
Camille's similarly indexed strings do not by themselves prove such a root.

The census was reproduced from the existing controller audit, MonoBehaviour
object index, and generated actor/effect prefab markers. It did not run a
second broad AnimeStudio export. Use the object index only for the fields it
actually contains, not as an effect-prefab catalog.
