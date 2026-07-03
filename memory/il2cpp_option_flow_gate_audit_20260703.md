# IL2CPP Option Flow Gate Audit - 2026-07-03

## Scope

This pass reran the focused offline IL2CPP option-flow chain against the cached
Endfield metadata and current `GameAssembly.dll` mapping.

The goal was to check whether the remaining timeline option groups can be
promoted from adjacency-style inferred responses to runtime-backed route
evidence.

## Commands

```bat
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --only-focus --body-context 4
python tools\endfield-il2cpp\map_body_targets_to_gameassembly.py
python scripts\story_recovery\build_timeline_option_flow_audit.py --language CN --il2cpp-report reports\option_flow_body_targets_gameassembly.json --only-interesting
```

## Results

- Metadata cache: `export_full/recovered/il2cpp/global-metadata.dat`
- Metadata version: `29`
- Metadata SHA-256: `cf822277f316021dabdce1f21249a01d016e411cea08daf7daa49973e54cc2df`
- Focused option-flow types: `12`
- Body targets mapped to GameAssembly: `30/30`
- Resolved direct calls: `209`
- Dialog-related direct calls: `63`
- Direct calls to catalog targets: `14`
- Timeline inferred response groups audited: `14`
- Groups with nonzero candidate trunk raw `optionIndex`: `0`
- Groups with all-zero candidate runtime fields: `14`

The generated reports were:

- `reports/option_flow_runtime_metadata_focus.md`
- `reports/option_flow_runtime_metadata_focus_diff.md`
- `reports/option_flow_body_targets_gameassembly.md`
- `reports/timeline_option_flow_audit_CN_interesting.md`

## Conclusion

No option-flow runtime metadata drift was detected. The IL2CPP body mapping
still supports the active clip gate model: `TryTriggerTrunkBindingOption` only
calls `SetDialogOption` for active clips whose runtime `+0x18` option field is
positive.

All 14 audited candidate response groups still have strict nonzero serialized
option rows but all-zero candidate runtime fields. They should remain
`doNotPromoteWithoutRuntimeRule`; adjacency alone is not enough evidence to
recover these routes safely.

