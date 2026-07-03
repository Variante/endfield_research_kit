# Hotfix Audio Source Graph Recovery - 2026-07-03

## Context

`reports/mission_order/hotfix_audio_event_audit.json` parses
`Data/Audio/PCK/Windows/Hotfix/hotfix_main.pck` directly and finds exact media
and event-hash evidence, but the source graph previously only ingested the
normal decoded audio index. Hotfix audio therefore stayed outside graph queries
even though the audit had concrete Wwise relationships.

The audit reports no known event-name hits, so the graph should not promote
these hashes to normal named `wwise_event` nodes.

## Change

`tools/endfield_source_graph.py` now ingests the hotfix audit after normal
decoded audio.

New node kinds:

- `hotfix_audio_pck`
- `hotfix_wwise_event_hash`

Shared existing node kinds:

- `wwise_media`
- `wwise_bank`
- `file` rows for decoded probe `.wem` files

New edges:

- `has_hotfix_audio_pck`
- `hotfix_pck_has_event_hash`
- `hotfix_event_hash_in_bank`
- `hotfix_bank_has_event_hash`
- `hotfix_event_hash_uses_media`
- `hotfix_media_used_by_event_hash`
- `hotfix_media_decoded_file`
- `decoded_audio_file_hotfix_media`
- `hotfix_pck_contains_media`
- `hotfix_media_has_event_hash_evidence`

The event hashes remain hotfix-specific evidence nodes and do not become named
`wwise_event` nodes until a real event-name source is found.

## Validation

Static checks passed:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

A focused temporary database called only `ingest_hotfix_audio_event_audit()`
against the real audit JSON. Results:

| Item | Count |
|---|---:|
| `hotfix_audio_pck` nodes | 1 |
| `hotfix_wwise_event_hash` nodes | 4 |
| `wwise_media` nodes | 23 |
| `wwise_bank` nodes | 4 |
| `has_hotfix_audio_pck` edges | 1 |
| `hotfix_pck_has_event_hash` edges | 4 |
| `hotfix_event_hash_uses_media` edges | 23 |
| `hotfix_media_used_by_event_hash` edges | 23 |
| `hotfix_media_decoded_file` edges | 23 |
| `decoded_audio_file_hotfix_media` edges | 23 |
| `hotfix_pck_contains_media` edges | 23 |
| `hotfix_event_hash_in_bank` edges | 4 |
| `hotfix_bank_has_event_hash` edges | 4 |
| `hotfix_media_has_event_hash_evidence` edges | 23 |
| named `wwise_event` nodes created by this ingest | 0 |

All 23 `hotfix_event_hash_uses_media` edges pointed at existing
`wwise_media` nodes in the temp database.

## Notes

This improves audio evidence coverage without implying that the hotfix event
hashes are known named gameplay events. Keep hotfix-specific edge kinds when
answering audio provenance questions so they do not get confused with normal CN
dialog or decoded-audio event evidence.
