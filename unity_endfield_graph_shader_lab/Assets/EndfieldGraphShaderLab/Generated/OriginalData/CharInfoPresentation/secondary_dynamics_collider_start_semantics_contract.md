# Collider Start Burst semantic contract

Status: `unique_static_semantic_candidate_wrapper_mapping_unresolved`.

This report follows each opaque export's static function-pointer slot through the pinned CPU-variant initializers and compares the resulting implementation bodies with the canonical 17-parameter Collider Start signature and managed fallback. It does not assert that method 385416 selected any hash; runtime GetProcAddress telemetry remains the wrapper-to-hash gate.

| Export candidate | Call order | AVX2 core | SSE2 core | Managed-fallback semantic match |
|---|---|---|---|---|
| `4aa6773b1eaf6055e0feb9593e092585` | `['param16', 'param2', 'param3', 'param4', 'param5', 'param6', 'param7', 'param8', 'param9', 'param10', 'param11', 'param12', 'param13', 'param14', 'param15', 'param16', 'param17']` | `0x24fa60` | `0xb5450` | `False` |
| `7342567c29c434b5b924be51bd8e34b7` | `['param1', 'param2', 'param3', 'param4', 'param5', 'param6', 'param7', 'param8', 'param9', 'param10', 'param11', 'param12', 'param13', 'param14', 'param15', 'param16', 'param17']` | `0x284c50` | `0xf4100` | `False` |
| `8b3d2761aaaac71a35d4a2557d570456` | `['param1', 'param2', 'param3', 'param4', 'param5', 'param6', 'param7', 'param8', 'param9', 'param10', 'param11', 'param12', 'param13', 'param14', 'param15', 'param16', 'param17']` | `0x243810` | `0xa7e50` | `True` |

Semantic candidate: `8b3d2761aaaac71a35d4a2557d570456`. Mapping status: `unresolved_runtime_GetProcAddress_required`.

The semantic candidate is only a static export-body fingerprint. No Burst function pointer is loaded or called by this builder.
