# AudioDialog RTPC and override-event source graph recovery - 2026-07-03

## Context

`AudioDialog.json` carries authored per-dialog audio behavior metadata beyond
the WEM path and speaker channel. In particular:

- `RTPCMap*` fields assign RTPC parameter values to audio rows.
- `overrideWwiseEvent` can route an audio row through an explicit Wwise event
  family that differs from the file stem.

The source graph already modeled `audio` nodes, WEM paths, and speaker-channel
links from `AudioDialog`, but it did not expose RTPC assignments or override
events.

## Implementation

Updated `tools/endfield_source_graph.py` in the `AudioDialog` selected
structured-table branch.

New node kind:

- `audio_rtpc_parameter`

New edge families:

- `audio_has_rtpc_value`
- `audio_rtpc_parameter_used_by_audio`
- `audio_dialog_overrides_wwise_event`
- `wwise_event_overrides_audio_dialog`

RTPC edge data records:

- `dialogId`
- `field`
- `language`
- `value`
- `path`
- `speakerChannel`

Override-event edge data records:

- `dialogId`
- `path`
- `speakerChannel`

## Validation

Focused temp graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Then built `tmp/audio_dialog_rtpc_validation.sqlite` with only
`ingest_selected_structured_tables()`.

Observed counts:

- `audio` nodes from `AudioDialog`: 25,245
- `audio_rtpc_parameter` nodes: 4
- `audio_has_rtpc_value`: 1,206
- `audio_rtpc_parameter_used_by_audio`: 1,206
- RTPC field distribution:
  - `RTPCMap`: 1,197
  - `RTPCMapKR`: 9
- RTPC parameter assignment counts:
  - `1487055645`: 460
  - `-1527225897`: 644
  - `-1339670615`: 99
  - `-213626185`: 3
- `audio_dialog_overrides_wwise_event`: 839
- `wwise_event_overrides_audio_dialog`: 839
- distinct override Wwise events: 29

Smoke queries confirmed:

- RTPC parameter `1487055645` returns audio rows including
  `au_dlg_commvo_pelica_agree_03` and `au_dlg_e10m4_8_006`.
- `au_dlg_commvo_pelica_agree_03` links to RTPC parameter `1487055645`
  with value `-4.0`.
- override event `vo_narrating_special_radiocontinue` returns radio-continue
  audio rows through `wwise_event_overrides_audio_dialog`.
