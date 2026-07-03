# Main Story Order Comparison Source Graph Recovery - 2026-07-03

## Summary

Promoted `reports/mission_order/main_story_order_vs_override_CN.json` into the
source graph.

The report compares static recovered main-story order against the active
OCR/manual override for main-story missions matching `/^e\d/`. It is useful for
finding agreement, divergence, missing keys, recovered-only keys, confidence
labels, and sampled inversions. It is not gameplay-observed chronology proof.

## Node And Edge Shapes

New node kinds:

- `main_story_order_comparison`
- `main_story_order_status`
- `story_order_inversion_sample`
- `story_order_confidence`
- `story_order_source`
- `story_order_evidence_kind`

New edge kinds include:

- `main_story_order_audit_has_mission`
- `main_story_order_compares_mission`
- `mission_has_main_story_order_comparison`
- `main_story_order_comparison_status`
- `main_story_order_comparison_level`
- `main_story_override_order_position`
- `story_in_main_story_override_order`
- `main_story_recovered_order_position`
- `story_in_main_story_recovered_order`
- `story_order_recovery_confidence`
- `story_order_recovery_source`
- `story_order_recovery_evidence_kind`
- `main_story_order_missing_override_key`
- `main_story_order_recovered_only_key`
- `main_story_order_has_inversion_sample`
- `main_story_order_has_coarse_inversion_sample`

The builder runs this pass after story-source-link ingest and before
LevelScript property-flow ingest, keeping it near the story/runtime evidence
cluster without promoting any new canonical story order.

## Validation

Static checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Focused temporary graph ingest called only
`ingest_main_story_order_override_comparison()` against the current report.

Focused ingest counts:

| Item | Count |
| --- | ---: |
| `main_story_order_comparison` nodes | 58 |
| `main_story_order_status` nodes | 3 |
| `story_order_inversion_sample` nodes | 1,030 |
| `story_order_confidence` nodes | 2 |
| `story_order_source` nodes | 5 |
| `story_order_evidence_kind` nodes | 11 |
| `story` nodes | 1,893 |
| `mission` nodes | 58 |
| `level` nodes | 21 |
| `map` nodes | 3 |
| `dataset` nodes | 1 |
| `file` nodes | 1 |
| `main_story_order_audit_has_mission` edges | 58 |
| `main_story_order_compares_mission` edges | 58 |
| `mission_has_main_story_order_comparison` edges | 58 |
| `main_story_order_comparison_status` edges | 58 |
| `main_story_order_comparison_level` edges | 88 |
| `main_story_override_order_position` edges | 1,910 |
| `story_in_main_story_override_order` edges | 1,910 |
| `main_story_recovered_order_position` edges | 1,917 |
| `story_in_main_story_recovered_order` edges | 1,917 |
| `story_order_recovery_confidence` edges | 1,917 |
| `story_order_recovery_source` edges | 1,917 |
| `story_order_recovery_evidence_kind` edges | 3,416 |
| `main_story_order_missing_override_key` edges | 0 |
| `main_story_order_recovered_only_key` edges | 7 |
| `main_story_order_has_inversion_sample` edges | 637 |
| `story_order_inversion_left_story` edges | 637 |
| `story_order_inversion_right_story` edges | 637 |
| `main_story_order_has_coarse_inversion_sample` edges | 393 |
| `story_order_coarse_inversion_left_story` edges | 393 |
| `story_order_coarse_inversion_right_story` edges | 393 |
| `main_story_order_vs_override` file rows | 1 |

Status split:

| Status | Missions |
| --- | ---: |
| `divergent` | 1 |
| `exact` | 3 |
| `highly-divergent` | 54 |

## Notes

This graph pass supports questions like "where does this story key sit in the
override order versus static recovered order?" and "which missions are highly
divergent?". It should not be used as a stronger claim than the source report:
gameplay/server-event-controlled interleaves still need observed runtime,
hash-key, or control-flow evidence.
