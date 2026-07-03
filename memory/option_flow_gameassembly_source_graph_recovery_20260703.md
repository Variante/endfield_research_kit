# Option Flow GameAssembly Source Graph Recovery - 2026-07-03

## Scope

Promoted compact runtime-code evidence from:

```text
reports/option_flow_body_targets_gameassembly.json
reports/option_flow_active_clip_field_analysis.json
```

into `tools/endfield_source_graph.py`.

This connects IL2CPP metadata methods to mapped `GameAssembly.dll` body
targets, important direct-call edges, and runtime field-offset evidence used by
the Timeline option-flow audit.

## Source Evidence

`reports/option_flow_body_targets_gameassembly.json` currently reports:

- catalog body targets: `30`
- mapped body targets: `30`
- resolved direct calls: `209`
- dialog-related direct calls: `63`
- direct calls to catalog targets: `14`
- important direct-call edges: `14`
- extracted option-flow facts: `14`

`reports/option_flow_active_clip_field_analysis.json` currently reports:

- direct call edges: `14`
- edges with offset uses: `14`
- distinct runtime offsets: `18`

Important runtime offsets include:

- `+0x18` / `activeClipGate`: runtime active option-clip gate.
- `+0x28` / `playableOptionsList`: serialized options list passed from
  `DialogOptionPlayableAsset.GenPlayable` to `InitDialogOptions`.
- `+0x98` / `selectedOptionIndex`: option index passed into
  `DialogUtils.DialogChooseOption`.
- `+0xa0` / `managerCurrentIndex`: current option index source on
  `DialogTimelineManager`.
- `+0x200` / `selectedIndexStore`: selected option index storage.

## Graph Additions

New node kinds:

- `il2cpp_gameassembly_report`
- `il2cpp_gameassembly_body_target`
- `il2cpp_direct_call`
- `option_flow_runtime_field_analysis`
- `option_flow_runtime_field_offset`
- `option_flow_runtime_field_kind`
- `option_flow_runtime_field_use_edge`

Important edges:

- `il2cpp_gameassembly_has_body_target`
- `il2cpp_body_target_maps_method`
- `il2cpp_method_has_gameassembly_body`
- `il2cpp_gameassembly_important_direct_call`
- `il2cpp_method_emits_direct_call`
- `il2cpp_direct_call_targets_method`
- `il2cpp_method_direct_calls_method`
- `il2cpp_gameassembly_has_runtime_field_analysis`
- `option_flow_analysis_runtime_field_offset`
- `option_flow_runtime_field_has_kind`
- `il2cpp_method_uses_option_flow_runtime_field`
- `option_flow_runtime_field_observed_near_method`
- `option_flow_analysis_field_use_edge`
- `il2cpp_method_has_option_flow_field_use_edge`
- `option_flow_field_use_edge_targets_method`
- `option_flow_field_use_edge_uses_offset`

The ingest runs immediately after `ingest_runtime_metadata_focus_report()` so
method nodes from the IL2CPP metadata catalog are already present. The body
ingest also adds method-name, method-index, and method-token aliases for the
focused methods.

## Validation

Focused temp source-graph validation created
`tmp/source_graph_option_flow_gameassembly_validation.sqlite`, called
`ingest_runtime_metadata_focus_report()` and
`ingest_option_flow_gameassembly_report()`, then removed the temp database.

Observed node counts:

| kind | count |
| --- | ---: |
| `il2cpp_gameassembly_report` | 1 |
| `il2cpp_gameassembly_body_target` | 30 |
| `il2cpp_direct_call` | 14 |
| `option_flow_runtime_field_analysis` | 1 |
| `option_flow_runtime_field_offset` | 18 |
| `option_flow_runtime_field_kind` | 6 |
| `option_flow_runtime_field_use_edge` | 14 |

Observed edge counts:

| edge | count |
| --- | ---: |
| `il2cpp_gameassembly_has_body_target` | 30 |
| `il2cpp_body_target_maps_method` | 30 |
| `il2cpp_method_has_gameassembly_body` | 30 |
| `il2cpp_gameassembly_important_direct_call` | 14 |
| `il2cpp_method_emits_direct_call` | 14 |
| `il2cpp_direct_call_targets_method` | 14 |
| `il2cpp_method_direct_calls_method` | 14 |
| `option_flow_analysis_runtime_field_offset` | 18 |
| `il2cpp_method_uses_option_flow_runtime_field` | 62 |
| `option_flow_runtime_field_observed_near_method` | 53 |
| `option_flow_analysis_field_use_edge` | 14 |
| `option_flow_field_use_edge_uses_offset` | 41 |

Query checks:

```bat
python tools\endfield_source_graph.py query activeClipGate --db tmp\source_graph_option_flow_gameassembly_validation.sqlite --kind option_flow_runtime_field_kind --limit 12
python tools\endfield_source_graph.py query DialogChooseOption --db tmp\source_graph_option_flow_gameassembly_validation.sqlite --limit 12
```

`DialogChooseOption` now resolves to the IL2CPP method, its mapped
GameAssembly body target, the `_SelectIndexInTimeline +0xc1` direct-call edge,
its metadata parameters, and runtime-field evidence around `+0x98`.

## Current Interpretation

This does not promote new story branch routes by itself. It makes the runtime
evidence that blocks/permits future promotion queryable: active option clips are
gated by runtime field `+0x18`, selected option index evidence flows through
`+0x98` into `DialogChooseOption`, and authored option rows still need to be
bound to active runtime clips before inferred responses can be treated as
proven branch edges.
