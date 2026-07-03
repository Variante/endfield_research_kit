# InteractiveEvent metadata source graph recovery - 2026-07-03

## Scope

Expanded `tools/endfield_source_graph.py` so the runtime metadata focus report
also indexes the `Beyond.Gameplay.InteractiveEvent.*` rows from
`reports/buff_runtime_metadata.json`.

The existing ingest already covered `focusTypes`; this pass adds a narrow
subset from:

- `memberOnlyTypes`
- `matchedTypes`

It deliberately avoids ingesting all `4,952` matched types. Only exact
InteractiveEvent runtime class names and the generated
`Beyond_Gameplay_InteractiveEvent_*ForMemoryPack` serializer rows are added.

## Graph Behavior

The type-row ingest is now shared so fields, methods, method parameters, return
types, and referenced type indexes are indexed once per type. Separate report
edges preserve which metadata bucket mentioned the type:

- `il2cpp_metadata_report_focus_type`
- `il2cpp_metadata_report_member_only_type`
- `il2cpp_metadata_report_matched_type`

## Validation

Focused temp validation called only:

```text
SourceGraphBuilder.open()
SourceGraphBuilder.ingest_runtime_metadata_focus_report()
```

against `tmp/runtime_metadata_interactive_validate.sqlite`.

Observed node counts from `source = runtime_metadata_focus`:

| kind | count |
| --- | ---: |
| `file` | 1 |
| `il2cpp_metadata_report` | 1 |
| `il2cpp_type` | 431 |
| `il2cpp_field` | 367 |
| `il2cpp_method` | 878 |
| `il2cpp_parameter` | 919 |
| `il2cpp_image` | 3 |
| `il2cpp_unresolved_type_index` | 211 |
| `il2cpp_unresolved_type_usage` | 473 |

Bucket edge counts:

| edge | count |
| --- | ---: |
| `il2cpp_metadata_report_focus_type` | 12 |
| `il2cpp_metadata_report_member_only_type` | 26 |
| `il2cpp_metadata_report_matched_type` | 26 |

Query checks:

```bat
python tools\endfield_source_graph.py query "Beyond.Gameplay.InteractiveEvent.EnterThrowMode" --db tmp\runtime_metadata_interactive_validate.sqlite --kind il2cpp_type --limit 8
python tools\endfield_source_graph.py query bombLineEffectActionCfg --db tmp\runtime_metadata_interactive_validate.sqlite --kind il2cpp_field --limit 8
```

Both resolved to the expected IL2CPP type/field nodes.

## Recovered Field Names

Useful InteractiveEvent field evidence now queryable from the graph includes:

- `AddTag`: `target`, `tags`
- `RemoveAddedTag`: `target`, `tags`
- `RemoveTag`: `target`, `tags`
- `ClearAddedTag`: `target`
- `PlayAnimationAction` / `StopAnimationAction`: `target`, `name`
- `PlaySoundAction`: `soundEvent`, `target`
- `CastSkill`: `source`, `target`, `skillId`
- `AttachSkill`: `skillId`, `target`, `m_skillData`
- `ExitThrowMode`: `skillId`
- `AttachToInstigator`: `mountPoint`, `followData`
- `EnterThrowMode`: `skillId`, `aimMountPoint`, `aimOffset`,
  `aimRightOffset`, `angleCurve`, `layers`, `speed`, `fallSpeed`, `radius`,
  `bombRadius`, `maxDistance`, `bombLineEffectActionCfg`,
  `ignoreColliderOptions`, `secondCheckLayerMask`, `overlapRadius`,
  `m_skillData`
- `EnterThrowModeData`: the same runtime fields plus `valid` and `holder`

This evidence was used to rename the AnimeStudio InteractiveEvent action
decoder fields from generic mode/prefix labels to metadata-aligned
`target`/`source`/`name`/`soundEvent` output fields.
