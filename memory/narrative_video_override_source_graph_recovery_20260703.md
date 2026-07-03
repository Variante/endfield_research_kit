# Narrative Video Override Source Graph Recovery - 2026-07-03

## Scope

The narrative video override audit is now source-graph evidence. The ingest
uses `reports/narrative_video_override_audit_CN.json` and connects manual
attach/suppress decisions, filename-only candidates, and unresolved narrative
video groups to story keys, stems, video files, and existing WebUI video nodes.

This targets the original-data understanding gap where narrative videos were
known to be mostly recovered in the WebUI, but the manual correction evidence
was not queryable beside Story and video binding evidence.

## Graph Additions

New node kinds:

- `narrative_video_override_audit`
- `narrative_video_override_rule`
- `narrative_video_override_bucket`
- `narrative_video_override_status`
- `narrative_video_stem`
- `narrative_video_known_false_suppression`
- `narrative_video_filename_candidate`
- `narrative_video_unresolved_candidate`
- `narrative_video_candidate_status`

Important edges:

- `has_narrative_video_override_rule`
- `narrative_video_override_targets_story`
- `story_has_narrative_video_override_rule`
- `narrative_video_override_uses_stem`
- `narrative_video_override_copies_audio_from_story`
- `narrative_video_stem_key_candidate`
- `narrative_video_stem_has_standalone_story_key`
- `has_narrative_video_known_false_suppression`
- `has_narrative_video_filename_candidate`
- `has_narrative_video_unresolved_candidate`
- `narrative_video_unresolved_rel_video`

## Validation

Focused validation graph:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Then a temporary graph ingested videos, CN Story, video bindings, and the
narrative-video override audit.

Observed node counts:

- `narrative_video_override_audit`: 1
- `narrative_video_override_rule`: 5
- `narrative_video_stem`: 36
- `narrative_video_known_false_suppression`: 1
- `narrative_video_filename_candidate`: 24
- `narrative_video_unresolved_candidate`: 7
- `narrative_video_candidate_status`: 2

Observed edge counts:

- `has_narrative_video_override_rule`: 5
- `narrative_video_override_targets_story`: 5
- `narrative_video_override_uses_stem`: 5
- `narrative_video_override_copies_audio_from_story`: 1
- `has_narrative_video_known_false_suppression`: 1
- `has_narrative_video_filename_candidate`: 24
- `has_narrative_video_unresolved_candidate`: 7
- `narrative_video_unresolved_rel_video`: 18

Query checks:

- `cutscene_e1m1_6` resolves to the Story node and shows the
  `attachInline:cutscene_e1m1_6` override rule, plus existing narrative video
  edges to `f_cs_video_e1m1_1.mp4` and `m_cs_video_e1m1_1.mp4`.
- `cs_video_e1m1_1` with kind `narrative_video_stem` resolves to its override
  stem node, matched files, standalone key `video_cs_video_e1m1_1`, and story
  candidate `cutscene_e1m1_6`.
- `remotecomm_e1m2_1` with kind `narrative_video_stem` resolves to the
  filename-only candidate attached to `remotecomm_e1m1_1`.

## Interpretation

Narrative video recovery is now easier to audit from either side:

- story key to manual video rule,
- video stem to corrected story target,
- unresolved stem to generated-story candidate status,
- false filename match to explicit suppress evidence.

The remaining higher-value frontier from the parallel read-only explorer is
shader bytecode/snippet evidence. Current graph material links resolve shader
PathIDs, but do not yet expose exported shader variants, DXBC/SMOL-V snippets,
or sidecar decode/decompile evidence.
