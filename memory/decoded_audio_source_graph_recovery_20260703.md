# Decoded Audio Source Graph Recovery - 2026-07-03

## Finding

The generated decoded-audio index at
`export_full/structured/Audio/CN/index.json` already carries Wwise media IDs,
event names, event evidence, source banks, decoded file paths, and storage
roots. The source graph did not ingest that evidence, so graph lookups could
show story/audio table relationships but not the lower-level Wwise event ->
media -> decoded file -> bank chain.

`tools/endfield_source_graph.py` now ingests the decoded-audio index during
graph builds and adds focused event-resolved evidence:

- `wwise_media` nodes keyed by media ID;
- `wwise_bank` nodes keyed by bank ID, with bank path aliases;
- decoded audio file nodes for event-resolved WAV/WEM outputs;
- event/media/file/bank edges from decoded index entries and event evidence.

The ingest is guarded by `export_full/structured/Audio/<LANG>/index.json`
existence so builds without decoded audio skip this step cleanly.

## Validation

Cheap checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Missing-index smoke check:

```text
decoded datasets 0
```

Focused decoded-audio ingest from the first broader implementation:

```bat
python -c "... SourceGraphBuilder(db_path='tmp/decoded_audio_ingest_only.sqlite').ingest_decoded_audio_index() ..."
```

Resulting counts:

| Item | Count |
| --- | ---: |
| nodes | 135,585 |
| edges | 203,332 |
| aliases | 57,064 |
| files | 79,329 |
| `wwise_media` nodes | 54,822 |
| `wwise_bank` nodes | 698 |
| `wwise_event` nodes | 735 |
| decoded audio files | 79,328 |
| `wwise_event_uses_media` edges | 2,191 |
| `wwise_media_decoded_file` edges | 54,822 |
| `wwise_media_from_bank` edges | 2,191 |
| `wwise_event_in_bank` edges | 1,859 |
| `decoded_audio_index_has_event_evidence` edges | 678 |

The decoded index has 79,793 entries. Of those, 55,287 entry rows and all
1,152 event rows carry numeric media IDs. The 24,506 nonnumeric entry IDs are
story/dialog `au_*` voice IDs, so they remain decoded file evidence instead of
being promoted to `wwise_media` nodes.

Follow-up validation showed that promoting every generic decoded entry into
graph file/media edges bloated quick-build databases and made final SQLite
analysis unstable. The maintained path now uses the full `events` and
`eventEvidence` sections for concrete event -> media -> decoded file -> bank
links, while preserving the full decoded-file inventory counts in the dataset
node payload.

The source-graph finalization step no longer runs full `ANALYZE`. Indexes are
created explicitly during schema setup, and the full analysis pass was the part
that repeatedly terminated large validation builds after ingestion had already
written a valid database.

Sample query:

```bat
python tools\endfield_source_graph.py query 107294543 --kind wwise_media --db tmp\decoded_audio_ingest_only.sqlite --limit 6
```

This resolves media `107294543` to:

- decoded file `export_full/structured/Audio/shared/wwise/ambience/107294543.wav`;
- event `au_amb_emitter_dg002_Tomblight_a`;
- bank `audit_banks.pck`;
- both direct decoded-entry evidence and `eventEvidence.mediaIds[0]`.

Another sample:

```bat
python tools\endfield_source_graph.py query au_music_cs_e8m2_1 --db tmp\decoded_audio_ingest_only.sqlite --limit 8
```

This resolves the Wwise event and bank evidence for `default_banks.pck`.

Post-commit smoke build with gameplay enabled and asset maps, reference rows,
and followups skipped, using a traced wrapper around
`SourceGraphBuilder.build()`:

```bat
python -u -X faulthandler -c "... TracedBuilder(db_path='tmp/audio_trace.sqlite', include_asset_maps=False, include_reference_rows=False, emit_followups=False).build() ..."
```

Result:

- nodes: `1,691,485`
- edges: `3,198,908`
- aliases: `2,280,897`
- files: `497,095`
- `wwise_media`: `1,101`
- `wwise_bank`: `698`
- `wwise_event`: `2,266`
- `decoded_audio`: `1,101`
- `wwise_event_uses_media`: `2,191`
- `wwise_media_decoded_file`: `1,101`

`python tools\endfield_source_graph.py query 120256210 --db tmp\audio_trace.sqlite --limit 12`
returned the expected decoded file
`export_full/structured/Audio/shared/wwise/unknown/120256210.wav`, bank
`default_banks.pck`, and event `au_int_matrix_core_hit_ground` relationships.

`python tools\endfield_source_graph.py query au_int_matrix_core_hit_ground --db tmp\audio_trace.sqlite --limit 16`
returned the event evidence, bank edges, and decoded media links.

## Follow-Up

The audio graph validation databases are disposable. Delete
`tmp/decoded_audio_ingest_only.sqlite`, `tmp/audio_min.sqlite`,
`tmp/audio_trace.sqlite`, and any interrupted `tmp/audio_index_source_graph*.sqlite`
after recording counts.

Next recovery experiment: compare AnimeStudio and patched fluffy-dumper on
`hotfix-audio` VFS coverage, then decide whether the decoded-audio builder or
source graph should ingest hotfix-specific event/media evidence.
