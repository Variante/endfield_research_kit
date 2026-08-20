# Secondary dynamics managed integrator boundary

Status: `native_spans_hash_pinned_managed_integrator_boundary`.

managed_end_step_helper_chain_only_burst_solver_unresolved

Indexed method `385708` span `0x18676e964..0x18676f784` (3616 bytes), body hash `0b5d95b2c3da269554beb03aefabc2b5e6bdd6f2aa897943e1c4328e45e4d77c`.

The fixed-client managed fallback reads the step/team and secondary-dynamics arrays, calls `TeamData.get_IsSpring`, `MathUtility.Project`, `ProjectOnPlane`, and `AutoToFloat3`, then writes velocity/friction/old-position array values. These are static byte facts, not Burst or transform equivalence.

| Helper method | Span | Direct calls |
|---|---|---:|
| `384698 get_IsSpring` | `0x18673dee8..0x18673df3c` (84 B) | 3 selected |
| `386213 Project` | `0x186696ac8..0x186696b50` (136 B) | 2 selected |
| `386214 ProjectOnPlane` | `0x1866b0cb4..0x1866b0d70` (188 B) | 3 selected |
| `386216 AutoToFloat3` | `0x184d87200..0x184d87230` (48 B) | 0 selected |

Branches pinned: 28; memory sites pinned: 20; selected helper edges: 7.
