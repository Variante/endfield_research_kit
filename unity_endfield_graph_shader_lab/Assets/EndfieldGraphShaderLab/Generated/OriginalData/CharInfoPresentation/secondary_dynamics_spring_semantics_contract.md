# Secondary dynamics Spring static semantics

Status: `managed_spring_static_semantics_closed`.

Method 385698 spans `0x186775ae4..0x186776080` (1436 bytes) with body hash `149382eea39d5d1a3ca0e27ed701a665f51406664766283b070305adc52050b5`.

This is a managed helper boundary, not a solver or Burst-equivalence claim.

| Evidence | Count |
|---|---:|
| direct calls | 29 |
| branch edges | 22 |
| RIP constants | 4 |
| memory sites | 16 |

The helper reads `simulationPower`/`simulationDeltaTime`, four direct `SpringConstraintParams` fields, `double3`/`quaternion` value arguments, and writes `nextPos`; it has no NativeArray operand or recoverable array stride.

The IFix patch gate and fallback call are preserved as native control-flow evidence. Runtime patch state, Burst execution, scheduling, and transform fidelity remain open.
