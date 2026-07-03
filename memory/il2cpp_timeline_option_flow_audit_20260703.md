# IL2CPP timeline option-flow audit

Date: 2026-07-03

## Scope

Refresh the local IL2CPP option-flow evidence and test whether the remaining
high-signal inferred timeline option-response groups can be promoted from raw
Timeline clip fields or runtime body-target evidence.

Commands run:

```bat
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --only-focus --body-context 4
python tools\endfield-il2cpp\map_body_targets_to_gameassembly.py
python scripts\story_recovery\build_timeline_option_flow_audit.py --language CN --il2cpp-report reports\option_flow_body_targets_gameassembly.json --only-interesting
```

Important: pass the JSON GameAssembly report to
`build_timeline_option_flow_audit.py`. Passing the Markdown report runs, but the
audit cannot parse nested `methodBodySummary.optionFlowFacts` from Markdown and
will report `facts: 0`.

## Metadata and GameAssembly status

Focused metadata catalog:

```text
metadata: export_full\recovered\il2cpp\global-metadata.dat
version: 29
size: 58,618,724
sha256: cf822277f316021dabdce1f21249a01d016e411cea08daf7daa49973e54cc2df
matched focus types: 12
metadata drift: none
```

GameAssembly mapping:

```text
mapped body targets: 30/30
resolved direct calls: 209
dialog-related direct calls: 63
direct calls to catalog targets: 14
extracted option-flow facts: 14
```

Useful runtime facts included in the audit:

- `DialogOptionPlayableAsset.GenPlayable` passes serialized option rows into
  `DialogOptionBehaviour.InitDialogOptions`.
- `DialogTimelineManager.SelectIndex` records the UI selection, calls
  `_SelectIndexInTimeline`, then calls `ResetDialogOption`.
- `_SelectIndexInTimeline` looks up the selected Timeline option object with
  the UI index and passes its `+0x98` field to `DialogChooseOption`.
- `DialogChooseOption` writes the selected option index into a runtime
  option/playable object `+0x18` field.
- `TryTriggerTrunkBindingOption` calls `SetDialogOption` only for an active
  clip whose runtime `+0x18` option field is positive.
- `SetDialogOption` compares the manager option `+0x18` with the candidate
  option `+0x18`, and treats zero as non-branch/default.
- `OnJumpForward` stops playback state, but has no direct option
  choose/set/reset call in the recovered body.

## Timeline audit result

Generated reports:

```text
reports\timeline_option_flow_audit_CN_interesting.md
reports\timeline_option_flow_audit_CN_interesting.json
```

Summary:

```text
Inferred response groups audited: 14
Groups with nonzero candidate trunk raw optionIndex: 0
Candidate trunk raw optionIndex counts: {'0': 33}
Candidate line raw optionIndex patterns: {'allZero': 14}
Candidate line clipOptionIndex patterns: {'allZero': 14}
Runtime gate verdicts: {'strictOptionRowsButAllZeroCandidateRuntimeField': 14}
Classification counts: {'rawTrunkClipOptionIndexDefaultAdjacent': 14}
Recommendation counts: {'doNotPromoteWithoutRuntimeRule': 14}
IL2CPP option-flow facts included: 14
```

One group, `dlg_c28m3_23` group `1`, has a nonzero runtime field elsewhere in
the window. The audit explains it as another option row:

```text
nonzeroOutside=dlg_c28m3_23_014
candidateAnchorsOtherOption=dlg_c28m3_23_010
runtimeMatchesOtherOption=dlg_c28m3_23_014->option_dlg_c28m3_23_2_001
```

So it is not evidence for the audited group.

## Conclusion

This pass does not recover new option routes. It strengthens the negative
evidence: the runtime body-target chain says active Timeline option branches
need a positive runtime option field, but all 14 audited candidate response
groups have zero candidate raw/clip runtime fields. The correct WebUI behavior
is to keep these as inferred/adjacency-only responses and not promote them to
runtime-backed option routes without a separate runtime rule or new nonzero
Timeline evidence.

Next useful direction: audit option groups outside the current
`--only-interesting` subset for nonzero raw/clip runtime fields, or target
runtime body decoding around how serialized option row `+0x98` is populated
before `_SelectIndexInTimeline`.
