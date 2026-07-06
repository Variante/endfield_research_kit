# MonoBehaviour SoundName Audio Source-Graph Recovery - 2026-07-06

## Scope

This pass connected decoded managed-reference sound fields from recovered
MonoBehaviour JSON to source-graph audio nodes.

The source graph already indexed decoded MonoBehaviour frontier entries and many
table/story audio relationships. The missing bridge was the deferred background
item from `memory/improvement_plan_20260701.md`: decoded managed-reference
`soundName` values were present in recovered JSON, but they were not emitted as
audio edges from the MonoBehaviour frontier entries.

## Added Edges

- `monobehaviour_frontier_entry_uses_audio`
- `audio_used_by_monobehaviour_frontier_entry`

The classifier is intentionally narrow. It only treats string scalar fields as
audio when the field is `soundName`, `audioEventKey`, or `eventName` and the
value is a full `au_*` audio id match. This links proven event-name strings
without broadening unrelated generic event fields.

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:
`tmp/managed_ref_sound_validate.sqlite`

The focused validation loaded a real decoded
`PlaySoundByParticleCount` payload:

`export_full/recovered/AnimeStudio-cli/Persistent/json_by_type/MonoBehaviour/MonoBehaviour#248136_p962CB143E48435A4.json`

It extracted one audio ref:

- `au_amb_indie_ccdg001_tech2103_oneshot`
  from `$.references.RefIds[].data.soundName`

Focused edge counts:

| Edge kind | Count |
| --- | ---: |
| `monobehaviour_frontier_entry_uses_audio` | 1 |
| `audio_used_by_monobehaviour_frontier_entry` | 1 |

Read-only decoded-group scan across `*PlaySound*.json` group files:

| Metric | Count |
| --- | ---: |
| PlaySound-related group files | 4 |
| Entries with extracted audio refs | 250 |
| Extracted audio ref edges | 250 |
| Unique audio values | 23 |
| Entries without matching `au_*` audio refs | 30 |

Top observed values:

| Audio id | Entries |
| --- | ---: |
| `au_sfx_ls_dung02_dg002_e9m2_zipline06` | 84 |
| `au_amb_indie_ccdg001_tech2103_oneshot` | 52 |
| `au_amb_emitter_electric_spark_01` | 42 |
| `au_amb_emitter_damagefire_largelorlong_01` | 25 |
| `au_amb_emitte_rmap02_fire_tiny` | 9 |

## Interpretation

This does not prove runtime playback conditions, attenuation, looping behavior,
or bank/media availability. It does make decoded effect-logic sound references
queryable from the same graph as Story, table audio, decoded Wwise media, and
MonoBehaviour frontier entries.
