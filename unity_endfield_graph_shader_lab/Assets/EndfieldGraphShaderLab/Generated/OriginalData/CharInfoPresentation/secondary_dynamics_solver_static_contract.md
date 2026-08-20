# Secondary dynamics solver static boundary

Status: `native_spans_hash_pinned`.

managed_fallback_accesses_closed_burst_solver_unresolved

| Method | Role | Span | Solver classification | Next callee |
|---|---|---:|---|---|
| 385696 Execute | managed_dispatch_wrapper | `0x186775a4c..0x186775ae4` (152 B) | wrapper_only | 385697 `0x186774be8` |
| 385697 Execute(int) | managed_fallback | `0x186774be8..0x186775a4c` (3684 B) | managed_fallback_observed | 385698 `0x186775ae4`, 385699 `0x186776704` |
| 385698 Spring | managed_helper | `0x186775ae4..0x186776080` (1436 B) | helper_only | — |
| 385699 Wind | managed_helper | `0x186776704..0x186776b64` (1120 B) | helper_only | — |
| 385700 WindForceBlend | managed_helper | `0x186776394..0x186776704` (880 B) | helper_only | — |
| 385701 UnsafeDo | burst_range_dispatch_wrapper | `0x186776080..0x186776394` (788 B) | wrapper_only_burst_solver_unresolved | 385542 `0x1867744b0`, 385570 `0x1867775fc` |
| 385450 Execute | managed_dispatch_wrapper | `0x186761580..0x186761618` (152 B) | wrapper_only | 385451 `0x186761618` |
| 385451 Execute(int) | managed_fallback | `0x186761618..0x1867624ac` (3732 B) | managed_fallback_observed | — |
| 385452 UnsafeDo | burst_range_dispatch_wrapper | `0x1867624ac..0x1867626d4` (552 B) | wrapper_only_burst_solver_unresolved | 385394 `0x186761454` |
| 385454 Execute | managed_dispatch_wrapper | `0x18675aa6c..0x18675ab00` (148 B) | wrapper_only | 385455 `0x18675a9cc` |
| 385455 Execute(int) | managed_fallback | `0x18675a9cc..0x18675aa6c` (160 B) | managed_fallback_observed | — |
| 385456 UnsafeDo | burst_range_dispatch_wrapper | `0x18675ab00..0x18675abbc` (188 B) | wrapper_only_burst_solver_unresolved | 385295 `0x18675a944` |

The indexed managed Execute bodies are the only rows with observed element arithmetic. Strides and element field displacements are evidence from the pinned x64 body; Burst range wrappers are not solver implementations.
