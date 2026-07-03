# NPC proxy env-talk source graph recovery - 2026-07-03

## Context

`NpcProxyTable.json`, `NpcProxyExDataTable.json`, and
`AtmosphericNpcClusterDataTable.json` carry authored ownership links for
world NPC proxies, environmental talk, mission-scoped dialog unlocks, and
atmospheric NPC clusters. The source graph already had WebUI story, env-talk,
NPC, and decoded world-entity text registry nodes, but it did not expose these
GameplayConfig proxy rows as first-class semantic owners.

## Implementation

Added `SourceGraphBuilder.ingest_npc_proxy_world_dialog_semantics()` in
`tools/endfield_source_graph.py`, wired after `npcVoiceBark` so `env_talk`
nodes are available before proxy ownership edges are added.

New semantic node kinds:

- `npc_proxy`
- `npc_proxy_ex_entry`
- `atmospheric_npc_cluster`
- `npc_proxy_name`

Primary new edge families:

- `defines_npc_proxy`
- `npc_proxy_in_level` / `level_has_npc_proxy`
- `npc_proxy_on_map` / `map_has_npc_proxy`
- `npc_proxy_uses_env_talk` / `env_talk_used_by_npc_proxy`
- `npc_proxy_has_ex_entry`
- `npc_proxy_ex_entry_targets_story` / `story_targeted_by_npc_proxy_ex_entry`
- `npc_proxy_ex_entry_in_mission` / `mission_has_npc_proxy_ex_entry`
- `npc_proxy_info_uses_npc_name` / `npc_proxy_name_used_by_proxy`
- `atmospheric_cluster_in_level` / `level_has_atmospheric_cluster`
- `atmospheric_cluster_uses_env_talk` / `env_talk_used_by_atmospheric_cluster`
- `atmospheric_cluster_has_npc` / `environmental_npc_in_atmospheric_cluster`
- `npc_proxy_brief_matches_authored_proxy` / `npc_proxy_has_brief`

## Validation

Focused temp graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Then built `tmp/npc_proxy_bridge_validation.sqlite` with only:

- `ingest_webui_story()`
- `ingest_npc_voice_bark_semantics()`
- `ingest_npc_proxy_world_dialog_semantics()`

Counts from the focused validation graph:

- `npc_proxy` nodes: 1,948
- `defines_npc_proxy` edges from `NpcProxyTable`: 1,601
- `npc_proxy_ex_entry` nodes: 2,272
- `npc_proxy_has_ex_entry` edges: 2,272
- `npc_proxy_ex_entry_targets_story` edges: 880
- distinct proxy-ex story targets: 826
- proxy-ex story target edges hitting existing WebUI story nodes: 753
- proxy-ex story target edges using placeholder story nodes: 106, covering
  101 distinct dialog IDs not present in the current CN WebUI story data
- `npc_proxy_uses_env_talk` / `env_talk_used_by_npc_proxy` edges: 218
- `atmospheric_npc_cluster` nodes: 410
- `atmospheric_cluster_uses_env_talk` edges: 370
- `atmospheric_cluster_has_npc` edges: 981

Smoke queries confirmed:

- `a1m6d1hsfarmer1_map02_v1d1d0_002` now links to
  `envTalk_a1m6d1_1`, `map02_lv002`, `map02`, `a1m6d1hsfarmer1`, and
  proxy-ex entries.
- `envTalk_a1m6d1_1` has the reverse
  `env_talk_used_by_npc_proxy` ownership edge.
- `base01_lv001_data_sub_npc_v1d0_cluster_001` links to
  `envTalk_base01_lv001_env_1`, `base01_lv001`, and its authored
  atmospheric NPC IDs.
- `dlg_a1m6d1_4` has reverse
  `story_targeted_by_npc_proxy_ex_entry` edges from two proxy-ex entries.

## Caveats

Proxy-ex dialog IDs that are absent from generated CN WebUI story data are
kept as placeholder `story` nodes, preserving the authored reference instead
of silently dropping it. Those missing dialog IDs are follow-up evidence for
story recovery coverage, not a failure of the proxy bridge.
