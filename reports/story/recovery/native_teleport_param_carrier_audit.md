# Native Value Carrier Audit: Beyond.Gameplay.TeleportParam

- Native size: **0x38**
- Signature methods / mapped pointers: **15 / 14**
- Nested container paths: **10**
- Direct callsites / carrier arguments: **13 / 10**
- Validation: **validated**
- GameAssembly SHA-256: `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
- Metadata SHA-256: `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`

## Focus fields

| Field | Offset | Reads | Writes | Zero writes | Direct initializer states |
|---|---:|---:|---:|---:|---|
| `missionId` | `0x18` | 3 | 2 | 1 | forwarded_or_unresolved=3, unknown=1, zero=6 |
| `levelScriptId` | `0x20` | 4 | 2 | 1 | forwarded_or_unresolved=3, unknown=1, zero=6 |
| `actionId` | `0x28` | 4 | 2 | 1 | forwarded_or_unresolved=3, unknown=1, zero=6 |
| `performId` | `0x30` | 4 | 2 | 1 | forwarded_or_unresolved=3, unknown=1, zero=6 |

## Boundary

The installed metadata defines the carrier layout and the installed GameAssembly defines every reported native pointer, direct callsite, field access, and local initializer. This bounded static audit does not claim coverage of virtual/interface dispatch, reflection, XLua, live server values, execution in a particular session, mission ownership, branch choice, or chronology.
