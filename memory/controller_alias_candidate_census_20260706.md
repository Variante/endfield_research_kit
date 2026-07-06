# Controller Alias Candidate Census - 2026-07-06

## Purpose

After adding `controllerAliasEntities` to the model binding candidate generator,
this pass regenerated the report into a temp directory and ranked rows where
model-view-state-controller clip/effect refs map to exported `asset_entity`
bases. This identifies unresolved model config rows that have stronger
alias evidence than ordinary name similarity.

## Validation Source

The generator was run against the current SQLite graph with `GRAPH_DIR`
redirected to:

```text
C:\Users\Xine\AppData\Local\Temp\source_graph_model_binding_validate
```

This avoids mutating ignored files under `reports/source_graph/` while still
testing the current generator against the real graph database.

The regenerated JSON reported:

- `controllerAliasCandidateRows=12`
- Status distribution among alias-bearing rows:
  - `no_exported_renderable_candidate`: 5
  - `runtime_only_or_unreferenced`: 6
  - `strong_exact_graph_edge`: 1

## Unresolved Rows With Controller Alias Candidates

These are the currently most actionable rows because the normal direct model id
or prefab-stem binding failed, but controller clip/effect refs point at exported
asset entities:

| Model id | World uses | Interactive uses | Alias entity |
| --- | ---: | ---: | --- |
| `int_switch_union_v2` | 20 | 0 | `interactive_universalswitch_1_001_01` |
| `int_door_experbase_v2_postmodel` | 0 | 2 | `interactive_organdoor_1_001_01` |
| `int_robot_fake_postmodel` | 0 | 2 | `interactive_zmdmachine_1_001_s01` |
| `int_system_fac_region_upgrade_postmodel` | 0 | 2 | `anm_fac_upgradebot_1_001_01` |
| `int_system_spaceship_credit_shop` | 0 | 2 | `anm_map01_zmdmachine_1_001_01` |

The first row is the strongest gameplay placement case because
`int_switch_union_v2` has 20 world-entity uses and the alias is supported by
four `A_interactive_universalswitch+1_001_01_*` clip refs plus the
`P_interactive_universalswitch+1_001_01` effect ref.

The remaining four rows have lower placement evidence, but their aliases are
still meaningful because they are tied through decoded model-view controller
refs rather than loose text search:

- `int_door_experbase_v2_postmodel` maps to organ-door clips/effect:
  `interactive_organdoor_1_001_01`.
- `int_robot_fake_postmodel` maps through
  `P_interactive_zmdmachine+1_001_s01` to
  `interactive_zmdmachine_1_001_s01`.
- `int_system_fac_region_upgrade_postmodel` maps through upgrade-bot clip and
  effect refs to `anm_fac_upgradebot_1_001_01`.
- `int_system_spaceship_credit_shop` maps through
  `P_anm_map01_zmdmachine+1_001_01` to
  `anm_map01_zmdmachine_1_001_01`.

## Full Alias Cluster

Across all 12 alias-bearing rows, the most frequent alias entities were:

- `interactive_organdoor_1_001_01`: 10 alias refs.
- `interactive_doorframe_1_001_02`: 8 alias refs.
- `interactive_universalswitch_1_001_01`: 5 alias refs.
- `interactive_door_1_005_01`: 5 alias refs.
- `interactive_console_1_001_01`: 4 alias refs.
- `anm_map02_gundoor_1_001_02`: 2 alias refs.
- `anm_fac_upgradebot_1_001_01`: 2 alias refs.

The model-id prefixes cluster around:

- `int_door`
- `int_switch`
- `int_indoor1`
- `int_console`
- `int_system`
- `int_robot`

## Interpretation

Controller aliases are a useful middle layer between conservative direct
renderable binding and speculative visual matching. They show that the game
data often names an interactive by gameplay role while the exported renderable
uses a visual-family name such as `interactive_universalswitch`,
`interactive_organdoor`, or `anm_fac_upgradebot`.

These aliases should not yet become direct renderable bindings. The correct
next step is to compare controller alias candidates against prefab or
AnimeStudio map evidence. If the same alias appears in prefab child references
or asset-map relations, it can be promoted from "controller alias candidate" to
a stronger binding class.

## Next Checks

- Inspect `int_door_experbase_v2_postmodel` next; it has a clean organ-door
  alias family and two interactive-template uses, making it a compact follow-up
  after switch-union.
- Add a graph query or CLI filter for `controllerAliasEntities` once the normal
  source-graph report refresh includes the new field.
- Compare alias families against raw prefab/AnimeStudio map evidence before
  changing any model binding status.
