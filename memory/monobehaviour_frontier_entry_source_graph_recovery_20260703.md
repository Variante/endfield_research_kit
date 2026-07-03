# MonoBehaviour Frontier Entry Source Graph Recovery - 2026-07-03

## Scope

The refreshed MonoBehaviour frontier now has entry-level source-graph evidence,
not just group counters. The ingest reads
`reports/monobehaviour_frontier_latest.json`, follows each residual group's
sidecar JSON under `tmp/decoded_index_mono_refreshed_20260703/groups/`, and
creates queryable nodes for the individual residual decoded JSON files.

This addresses the original understanding gap around partially decoded
MonoBehaviour/gameplay payloads. Queries can now show which exact source JSON,
PathID, source CAB, VFS chunk, schema, managed classes, layouts, fields, and
decode error prove a residual frontier item.

## Graph Additions

New node kinds:

- `monobehaviour_frontier_entry`
- `monobehaviour_decode_error`
- `monobehaviour_field`
- `monobehaviour_tag`
- `monobehaviour_source_file`
- `vfs_chunk`

New edges:

- `monobehaviour_frontier_group_source_file`
- `monobehaviour_frontier_group_entry`
- `monobehaviour_frontier_entry_file`
- `monobehaviour_frontier_entry_pathid`
- `monobehaviour_frontier_entry_source_file`
- `monobehaviour_frontier_entry_chunk`
- `monobehaviour_frontier_entry_status`
- `monobehaviour_frontier_entry_registry_status`
- `monobehaviour_frontier_entry_domain`
- `monobehaviour_frontier_entry_schema`
- `monobehaviour_frontier_entry_schema_group`
- `monobehaviour_frontier_entry_schema_kind`
- `monobehaviour_frontier_entry_field_set`
- `monobehaviour_frontier_entry_error`
- `monobehaviour_frontier_entry_field`
- `monobehaviour_frontier_entry_class`
- `monobehaviour_frontier_entry_layout`
- `monobehaviour_frontier_entry_tag`

## Validation

Static check:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Focused temp graph using only `ingest_monobehaviour_frontier_report()`:

- `monobehaviour_frontier_report`: 1
- `monobehaviour_frontier_group`: 21
- `monobehaviour_frontier_entry`: 746
- `monobehaviour_decode_error`: 2
- `monobehaviour_field`: 34
- `monobehaviour_source_file`: 663
- `vfs_chunk`: 7
- `monobehaviour_tag`: 10

Edges:

- `has_monobehaviour_frontier_group`: 21
- `monobehaviour_frontier_group_entry`: 746
- `monobehaviour_frontier_entry_error`: 688
- `monobehaviour_frontier_entry_schema`: 746
- `monobehaviour_frontier_entry_class`: 5,164
- `monobehaviour_frontier_entry_layout`: 9,425
- `monobehaviour_frontier_entry_file`: 746
- `monobehaviour_frontier_entry_chunk`: 746
- partial entry status edges: 734

Query checks:

- `ProjectileTemplateData --kind monobehaviour_schema` now lists concrete
  residual entries such as `data_projectile_chr_0004_pelica_combo_skill`.
- `data_projectile_chr_0004_pelica_combo_skill --kind
  monobehaviour_frontier_entry` shows its VFS chunk, classes,
  `camera/cinematic` domain, `EndOfStreamException`, fields, source file, and
  PathID.
- `EndOfStreamException --kind monobehaviour_decode_error` shows the residual
  entries sharing that decode failure signature.

## Interpretation

The current frontier is not broad unparsed data. It is concentrated in 734
partial entries across 21 groups, dominated by gameplay template tails:

- `ProjectileTemplateData`
- `AbilityEntityTemplateData`
- `EnemyTemplateData`
- `CharacterTemplateData`
- `LineFollower`

The repeated entry evidence shows common nested layouts around
`AbilitySystemData`, `SkillDataBundle`, `EffectActionCfg`, projectile roots,
entity roots, movement/model/navigation components, and blackboard vector/double
payloads. This turns the next decoder task into a specific class/layout/error
frontier rather than a generic MonoBehaviour gap.
