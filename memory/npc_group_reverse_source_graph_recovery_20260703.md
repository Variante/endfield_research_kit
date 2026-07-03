# NPC Group Reverse Source-Graph Recovery - 2026-07-03

## Scope

`NpcTable.npcGroupId` already produced `npc_in_group` edges from NPCs to NPC
groups. This pass adds the reverse group-to-NPC edge so queries starting from a
shared NPC group can discover all NPC rows that use it.

## Added Reverse Edge

- `npc_group_has_npc`

## Validation

Focused temp graph:
`tmp/npc_group_reverse_validate.sqlite`

The validation seeded `ingest_npc_voice_bark_semantics()` only.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `npc_in_group` | 359 | `npc_group_has_npc` | 359 |

Sample group:
`npc_group:npc_boy_unionscholar_a_02_g01` links back to
`npc:npc_lv005_yuanqu_b_i001` and `npc:npc_lv005_yuanqu_b_i002`.

`python -m py_compile tools\endfield_source_graph.py` passed.
