# Secondary dynamics Wind helper static boundary

Status: `native_spans_hash_pinned_wind_helpers`.

managed_helper_static_semantics_only_burst_solver_unresolved

| Method | Span | Branches | Constants | Direct calls |
|---|---:|---:|---:|---:|
| 385699 `Wind` | `0x186776704..0x186776b64` (1120 B) | 6 | 5 | 15 |
| 385700 `WindForceBlend` | `0x186776394..0x186776704` (880 B) | 2 | 12 | 23 |

Wind copies job-owned wind-index (4-byte), wind-data (0x98-byte), team-wind-data (0xd4-byte), and depth (4-byte) records before the two statically verified WindForceBlend calls. WindForceBlend has explicit minimum-magnitude and IFix branches and writes a 12-byte result; Burst dispatch and runtime behavior remain unresolved.
