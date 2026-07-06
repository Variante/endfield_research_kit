# Audio Usage Query Source Graph Recovery - 2026-07-06

## Summary

Added a focused `audio-usage` query shortcut to `tools/endfield_source_graph.py`
for reviewing audio ids, Story line audio references, path-backed AudioDialog
nodes, and audio-config usage relations from the source graph.

This is a diagnostic source-graph improvement only. It does not relink Story
audio, change WebUI output, decode new Wwise media, or infer matches between
unresolved Story audio ids and path-backed AudioDialog rows.

## New Query Surface

Use:

```bat
python tools\endfield_source_graph.py audio-usage au_dlg_a1m10_1_001 --kind audio --limit 5
python tools\endfield_source_graph.py audio-usage au_prts_tape0003_001 --kind audio --limit 5
python tools\endfield_source_graph.py audio-usage dlg_a1m10_1_001 --kind line --limit 5
```

The command resolves terms as `audio` by default, with optional forced lookup
for `line`, `dialog_text`, `radio_line`, `remote_common_line`, or
`responsive_response`. It returns the resolved seed node, aliases, adjacent
audio edge counts, explicit path evidence, caveats, and compact relation
samples.

Resolution is exact-first for audio ids, `.wem` path stems, and numeric
`AudioDialog` row ids before falling back to the generic graph lookup.

## Validation

Validated with:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py audio-usage au_dlg_a1m10_1_001 --kind audio --limit 5
python tools\endfield_source_graph.py audio-usage au_dlg_e1m1_5_001 --limit 8
python tools\endfield_source_graph.py audio-usage au_prts_tape0003_001 --kind audio --limit 5
python tools\endfield_source_graph.py audio-usage dlg_a1m10_1_001 --kind line --limit 5
python tools\endfield_source_graph.py audio-usage au_charGiftTalkid_1 --kind audio --limit 8
```

Observed `au_dlg_a1m10_1_001` as an unresolved Story/DialogText audio id with:

- `audio_used_by_line`: 1
- `uses_audio`: 1
- `audio_used_by_dialog_text`: 1
- `dialog_text_uses_audio`: 1
- no `audio_path`

Observed `au_dlg_e1m1_5_001` as a Story/DialogText audio id that also has
path-backed `AudioDialog` evidence:

- path `v1d0/Narrating/Episode_01/e1m1/au_dlg_e1m1_5_001.wem`
- speaker channel `chen`
- `audio_path`, `defines_audio`, `audio_voice_extra_for_audio`,
  `audio_used_by_line`, and `dialog_text_uses_audio` evidence
- caveats: `path_backed_audio`, `story_line_audio_reference`

Observed `au_prts_tape0003_001` as a path-backed AudioDialog audio node with:

- path `v1d0/Narrating/Fragment/PRTS_0003/au_prts_tape0003_001.wem`
- duration `3.7483959197998047`
- speaker channel `frgm_announcer`
- `audio_path`, `defines_audio`, `speaker_channel`, and
  `audio_voice_extra_for_audio` evidence.

Observed forced line lookup for `dlg_a1m10_1_001` resolving the Story line and
showing its `uses_audio` / `audio_used_by_line` relationship to
`au_dlg_a1m10_1_001`.

Observed `au_charGiftTalkid_1` as a Story/env-talk audio id with no path
evidence, plus caveats `no_audio_path_evidence`,
`story_line_audio_reference`, and `story_line_reference_unresolved_to_wem`.

## Boundary

This command makes the current graph boundary inspectable: some audio nodes are
path-backed AudioDialog media, while many WebUI Story line audio ids are still
semantic references without WEM path evidence. The command reports that
distinction rather than collapsing the two namespaces.
